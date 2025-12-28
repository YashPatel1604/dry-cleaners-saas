# payments/views.py

from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Sum, Count, Case, When, IntegerField
from django.db.models.functions import TruncDate
from django.utils import timezone

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from orders.services import recalc_order_totals
from .models import Payment, Adjustment
from .serializers import PaymentSerializer, AdjustmentSerializer


# =========================
# Payments
# =========================

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(tenant=self.request.tenant).select_related("order")

    # ✅ IDEMPOTENCY LAYER:
    # - If reference is provided and already exists (tenant+reference), return existing payment (200)
    # - Otherwise create normally (201)
    # - If race condition hits DB unique constraint, fetch+return existing (200)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = serializer.validated_data["order"]
        amount = serializer.validated_data["amount_cents"]
        reference = (serializer.validated_data.get("reference") or "").strip()

        # 🔒 settlement lock (TOP)
        if getattr(order, "settled_at", None) is not None:
            raise ValidationError(
                {"order": "Order is settled and cannot accept new payments."})

        # tenant isolation
        if order.tenant_id != self.request.tenant.id:
            raise ValidationError(
                {"order": "Order does not belong to this tenant."})

        # policy
        if order.status == "CANCELLED":
            raise ValidationError(
                {"order": "Cannot add payments to a cancelled order."})

        if int(amount) <= 0:
            raise ValidationError({"amount_cents": "Must be > 0."})

        # ✅ replay behavior (fast path)
        if reference:
            existing = (
                Payment.objects.filter(
                    tenant=self.request.tenant, reference=reference)
                .select_related("order")
                .first()
            )
            if existing:
                resp = Response(PaymentSerializer(existing).data, status=200)
                resp["Idempotent-Replay"] = "true"
                return resp

        # ✅ atomic create (handles race condition)
        try:
            with transaction.atomic():
                payment = serializer.save(
                    tenant=self.request.tenant, reference=reference)
        except IntegrityError:
            if reference:
                existing = (
                    Payment.objects.filter(
                        tenant=self.request.tenant, reference=reference)
                    .select_related("order")
                    .first()
                )
                if existing:
                    resp = Response(PaymentSerializer(
                        existing).data, status=200)
                    resp["Idempotent-Replay"] = "true"
                    return resp
            raise

        recalc_order_totals(order)
        return Response(PaymentSerializer(payment).data, status=201)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        payment = self.get_object()

        # 🔒 settlement lock (TOP)
        if getattr(payment.order, "settled_at", None) is not None:
            raise ValidationError(
                {"order": "Order is settled and payments cannot be voided."})

        if payment.status != Payment.Status.CAPTURED:
            raise ValidationError(
                {"payment": "Only CAPTURED payments can be voided."})

        payment.status = Payment.Status.VOIDED
        payment.save(update_fields=["status"])

        recalc_order_totals(payment.order)
        return Response({"ok": True})

    @action(detail=False, methods=["post"])
    def refund(self, request):
        """
        Create a refund payment (direction=OUT).
        Body: { "order": <id>, "amount_cents": 1234, "method": "CARD", "note": "...", "reference": "..." }
        """
        order_id = request.data.get("order")
        amount_cents = request.data.get("amount_cents")
        method = request.data.get("method")

        if not order_id:
            raise ValidationError({"order": "Required."})
        if amount_cents is None:
            raise ValidationError({"amount_cents": "Required."})

        try:
            amount_cents = int(amount_cents)
        except Exception:
            raise ValidationError({"amount_cents": "Must be an integer."})

        if amount_cents <= 0:
            raise ValidationError({"amount_cents": "Must be > 0."})

        if method not in Payment.Method.values:
            raise ValidationError(
                {"method": f"Invalid. Allowed: {list(Payment.Method.values)}"})

        # tenant-safe fetch
        try:
            order = self.request.tenant.orders.get(id=order_id)
        except Exception:
            raise ValidationError({"order": "Order not found in this tenant."})

        # 🔒 settlement lock (refunds become adjustments post-settle)
        if getattr(order, "settled_at", None) is not None:
            raise ValidationError(
                {"order": "Order is settled and refunds require an adjustment flow."})

        if order.status == "CANCELLED":
            raise ValidationError(
                {"order": "Refunds for CANCELLED orders require a policy; blocking for now."})

        recalc_order_totals(order)
        order.refresh_from_db(fields=["paid_cents"])
        net_paid = int(order.paid_cents)

        if amount_cents > net_paid:
            raise ValidationError(
                {"amount_cents": f"Refund exceeds net paid ({net_paid})."})

        refund = Payment.objects.create(
            tenant=self.request.tenant,
            order=order,
            method=method,
            status=Payment.Status.CAPTURED,
            direction=Payment.Direction.OUT,
            amount_cents=amount_cents,
            reference=(request.data.get("reference") or "").strip(),
            note=request.data.get("note", ""),
        )

        recalc_order_totals(order)
        return Response({"ok": True, "refund_id": refund.id})

    @action(detail=False, methods=["get"], url_path="daily-summary")
    def daily_summary(self, request):
        date_str = request.query_params.get("date")

        if date_str:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(
                    {"date": "Invalid format. Use YYYY-MM-DD."})
        else:
            day = timezone.localdate()

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(
            datetime.combine(day, datetime.min.time()), tz)
        end = start + timedelta(days=1)

        qs = self.get_queryset().filter(created_at__gte=start, created_at__lt=end)

        rows = (
            qs.values("method")
            .annotate(
                count=Count(Case(When(status=Payment.Status.CAPTURED,
                            then=1), output_field=IntegerField())),
                in_cents=Sum(Case(
                    When(direction=Payment.Direction.IN,
                         status=Payment.Status.CAPTURED, then="amount_cents"),
                    default=0, output_field=IntegerField()
                )),
                out_cents=Sum(Case(
                    When(direction=Payment.Direction.OUT,
                         status=Payment.Status.CAPTURED, then="amount_cents"),
                    default=0, output_field=IntegerField()
                )),
                voided_cents=Sum(Case(
                    When(status=Payment.Status.VOIDED, then="amount_cents"),
                    default=0, output_field=IntegerField()
                )),
                voided_count=Count(
                    Case(When(status=Payment.Status.VOIDED, then=1), output_field=IntegerField())),
            )
            .order_by("method")
        )

        by_method = []
        total_in = total_out = total_voided = total_count = total_voided_count = 0

        for r in rows:
            inc = int(r["in_cents"] or 0)
            outc = int(r["out_cents"] or 0)
            voidc = int(r["voided_cents"] or 0)
            cnt = int(r["count"] or 0)
            vcnt = int(r["voided_count"] or 0)

            by_method.append({
                "method": r["method"],
                "count": cnt,
                "in_cents": inc,
                "out_cents": outc,
                "net_cents": inc - outc,
                "voided_cents": voidc,
                "voided_count": vcnt,
            })

            total_in += inc
            total_out += outc
            total_voided += voidc
            total_count += cnt
            total_voided_count += vcnt

        return Response({
            "date": str(day),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "totals": {
                "count": total_count,
                "in_cents": total_in,
                "out_cents": total_out,
                "net_cents": total_in - total_out,
                "voided_cents": total_voided,
                "voided_count": total_voided_count,
            },
            "by_method": by_method,
        })

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")

        if not start_str:
            raise ValidationError({"start": "Required. Use YYYY-MM-DD."})
        if not end_str:
            raise ValidationError({"end": "Required. Use YYYY-MM-DD."})

        try:
            start_day = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_day = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError({"date": "Invalid format. Use YYYY-MM-DD."})

        if end_day < start_day:
            raise ValidationError({"end": "Must be on/after start."})

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(
            start_day, datetime.min.time()), tz)
        end = timezone.make_aware(datetime.combine(
            end_day, datetime.min.time()), tz) + timedelta(days=1)

        qs = self.get_queryset().filter(created_at__gte=start, created_at__lt=end)

        group = request.query_params.get("group")
        method_breakdown = request.query_params.get(
            "method_breakdown") in ("1", "true", "True")

        buckets = None
        if group == "day":
            day_rows = (
                qs.annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(
                    count=Count(
                        Case(When(status=Payment.Status.CAPTURED, then=1), output_field=IntegerField())),
                    in_cents=Sum(Case(
                        When(direction=Payment.Direction.IN,
                             status=Payment.Status.CAPTURED, then="amount_cents"),
                        default=0, output_field=IntegerField()
                    )),
                    out_cents=Sum(Case(
                        When(direction=Payment.Direction.OUT,
                             status=Payment.Status.CAPTURED, then="amount_cents"),
                        default=0, output_field=IntegerField()
                    )),
                    voided_cents=Sum(Case(
                        When(status=Payment.Status.VOIDED, then="amount_cents"),
                        default=0, output_field=IntegerField()
                    )),
                    voided_count=Count(
                        Case(When(status=Payment.Status.VOIDED, then=1), output_field=IntegerField())),
                )
                .order_by("day")
            )

            buckets = []
            for r in day_rows:
                inc = int(r["in_cents"] or 0)
                outc = int(r["out_cents"] or 0)
                voidc = int(r["voided_cents"] or 0)
                cnt = int(r["count"] or 0)
                vcnt = int(r["voided_count"] or 0)

                buckets.append({
                    "date": str(r["day"]),
                    "count": cnt,
                    "in_cents": inc,
                    "out_cents": outc,
                    "net_cents": inc - outc,
                    "voided_cents": voidc,
                    "voided_count": vcnt,
                })

            if not method_breakdown:
                return Response({
                    "start": start_str,
                    "end": end_str,
                    "group": "day",
                    "start_ts": start.isoformat(),
                    "end_ts_exclusive": end.isoformat(),
                    "buckets": buckets,
                })

        rows = (
            qs.values("method")
            .annotate(
                count=Count(Case(When(status=Payment.Status.CAPTURED,
                            then=1), output_field=IntegerField())),
                in_cents=Sum(Case(
                    When(direction=Payment.Direction.IN,
                         status=Payment.Status.CAPTURED, then="amount_cents"),
                    default=0, output_field=IntegerField()
                )),
                out_cents=Sum(Case(
                    When(direction=Payment.Direction.OUT,
                         status=Payment.Status.CAPTURED, then="amount_cents"),
                    default=0, output_field=IntegerField()
                )),
                voided_cents=Sum(Case(
                    When(status=Payment.Status.VOIDED, then="amount_cents"),
                    default=0, output_field=IntegerField()
                )),
                voided_count=Count(
                    Case(When(status=Payment.Status.VOIDED, then=1), output_field=IntegerField())),
            )
            .order_by("method")
        )

        by_method = []
        total_in = total_out = total_voided = total_count = total_voided_count = 0

        for r in rows:
            inc = int(r["in_cents"] or 0)
            outc = int(r["out_cents"] or 0)
            voidc = int(r["voided_cents"] or 0)
            cnt = int(r["count"] or 0)
            vcnt = int(r["voided_count"] or 0)

            by_method.append({
                "method": r["method"],
                "count": cnt,
                "in_cents": inc,
                "out_cents": outc,
                "net_cents": inc - outc,
                "voided_cents": voidc,
                "voided_count": vcnt,
            })

            total_in += inc
            total_out += outc
            total_voided += voidc
            total_count += cnt
            total_voided_count += vcnt

        payload = {
            "start": start_str,
            "end": end_str,
            "start_ts": start.isoformat(),
            "end_ts_exclusive": end.isoformat(),
            "totals": {
                "count": total_count,
                "in_cents": total_in,
                "out_cents": total_out,
                "net_cents": total_in - total_out,
                "voided_cents": total_voided,
                "voided_count": total_voided_count,
            },
            "by_method": by_method,
        }

        if buckets is not None:
            payload["group"] = "day"
            payload["buckets"] = buckets

        return Response(payload)


# =========================
# Adjustments
# =========================

class AdjustmentViewSet(viewsets.ModelViewSet):
    serializer_class = AdjustmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Adjustment.objects.filter(tenant=self.request.tenant).select_related("order")

    def perform_create(self, serializer):
        order = serializer.validated_data["order"]

        # 🔒 tenant isolation (TOP)
        if order.tenant_id != self.request.tenant.id:
            raise ValidationError(
                {"order": "Order does not belong to this tenant."})

        # ✅ adjustments are ONLY post-settlement
        if getattr(order, "settled_at", None) is None:
            raise ValidationError(
                {"order": "Order must be settled before adjustments are allowed."})

        if order.status == "CANCELLED":
            raise ValidationError(
                {"order": "Adjustments for CANCELLED orders require a policy; blocking for now."})

        # amount validation
        try:
            amount = int(serializer.validated_data["amount_cents"])
        except Exception:
            raise ValidationError({"amount_cents": "Must be an integer."})
        if amount <= 0:
            raise ValidationError({"amount_cents": "Must be > 0."})

        kind = serializer.validated_data.get("kind")
        direction = serializer.validated_data.get("direction")

        # ✅ Only allow IN adjustments for CREDIT_APPLIED
        if direction == Adjustment.Direction.IN and kind != Adjustment.Kind.CREDIT_APPLIED:
            raise ValidationError(
                {"direction": "IN adjustments are only allowed for CREDIT_APPLIED."})

        # ✅ prevent over-refund: OUT adjustments can't exceed current net paid
        recalc_order_totals(order)
        order.refresh_from_db(fields=["paid_cents"])
        net_paid = int(order.paid_cents)

        existing = order.adjustments.filter(status=Adjustment.Status.APPLIED)
        for a in existing:
            amt = int(a.amount_cents)
            if a.direction == Adjustment.Direction.IN:
                net_paid += amt
            else:
                net_paid -= amt

        if direction == Adjustment.Direction.OUT and amount > net_paid:
            raise ValidationError(
                {"amount_cents": f"Adjustment exceeds net paid ({net_paid})."})

        # save atomically; mark APPLIED by default
        serializer.save(tenant=self.request.tenant,
                        status=Adjustment.Status.APPLIED)

        # refresh derived totals used by receipts
        recalc_order_totals(order)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        adj = self.get_object()

        if adj.status != Adjustment.Status.APPLIED:
            raise ValidationError(
                {"adjustment": "Only APPLIED adjustments can be voided."})

        if getattr(adj.order, "settled_at", None) is None:
            raise ValidationError(
                {"order": "Order is not settled; voiding adjustments is blocked."})

        adj.status = Adjustment.Status.VOIDED
        adj.save(update_fields=["status"])

        recalc_order_totals(adj.order)
        return Response({"ok": True})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        /api/adjustments/summary/?start=YYYY-MM-DD&end=YYYY-MM-DD&group=day&kind_breakdown=1
        """
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")
        group = request.query_params.get("group")
        kind_breakdown = request.query_params.get(
            "kind_breakdown") in ("1", "true", "True")

        if not start_str:
            raise ValidationError({"start": "Required. Use YYYY-MM-DD."})
        if not end_str:
            raise ValidationError({"end": "Required. Use YYYY-MM-DD."})

        try:
            start_day = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_day = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError({"date": "Invalid format. Use YYYY-MM-DD."})

        if end_day < start_day:
            raise ValidationError({"end": "Must be on/after start."})

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(
            start_day, datetime.min.time()), tz)
        end = timezone.make_aware(datetime.combine(
            end_day, datetime.min.time()), tz) + timedelta(days=1)

        qs = self.get_queryset().filter(created_at__gte=start, created_at__lt=end)

        # only APPLIED counts financially
        base = qs.filter(status=Adjustment.Status.APPLIED)

        # optional buckets by day
        buckets = None
        if group == "day":
            day_rows = (
                base.annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(
                    in_cents=Sum(Case(
                        When(direction=Adjustment.Direction.IN,
                             then="amount_cents"),
                        default=0, output_field=IntegerField()
                    )),
                    out_cents=Sum(Case(
                        When(direction=Adjustment.Direction.OUT,
                             then="amount_cents"),
                        default=0, output_field=IntegerField()
                    )),
                    count=Count("id"),
                )
                .order_by("day")
            )

            buckets = []
            for r in day_rows:
                inc = int(r["in_cents"] or 0)
                outc = int(r["out_cents"] or 0)
                buckets.append({
                    "date": str(r["day"]),
                    "count": int(r["count"] or 0),
                    "in_cents": inc,
                    "out_cents": outc,
                    "net_cents": inc - outc,
                })

            if not kind_breakdown:
                return Response({
                    "start": start_str,
                    "end": end_str,
                    "group": "day",
                    "start_ts": start.isoformat(),
                    "end_ts_exclusive": end.isoformat(),
                    "buckets": buckets,
                })

        rows = (
            base.values("kind")
            .annotate(
                count=Count("id"),
                in_cents=Sum(Case(
                    When(direction=Adjustment.Direction.IN, then="amount_cents"),
                    default=0, output_field=IntegerField()
                )),
                out_cents=Sum(Case(
                    When(direction=Adjustment.Direction.OUT, then="amount_cents"),
                    default=0, output_field=IntegerField()
                )),
            )
            .order_by("kind")
        )

        by_kind = []
        total_in = total_out = total_count = 0

        for r in rows:
            inc = int(r["in_cents"] or 0)
            outc = int(r["out_cents"] or 0)
            cnt = int(r["count"] or 0)

            by_kind.append({
                "kind": r["kind"],
                "count": cnt,
                "in_cents": inc,
                "out_cents": outc,
                "net_cents": inc - outc,
            })

            total_in += inc
            total_out += outc
            total_count += cnt

        payload = {
            "start": start_str,
            "end": end_str,
            "start_ts": start.isoformat(),
            "end_ts_exclusive": end.isoformat(),
            "totals": {
                "count": total_count,
                "in_cents": total_in,
                "out_cents": total_out,
                "net_cents": total_in - total_out,
            },
            "by_kind": by_kind,
        }

        if buckets is not None:
            payload["group"] = "day"
            payload["buckets"] = buckets

        return Response(payload)
