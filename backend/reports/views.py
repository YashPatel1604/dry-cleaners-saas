import csv
import io
from datetime import date, datetime, timedelta

from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Max,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from tenants.permissions import IsTenantMember
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem
from payments.models import Adjustment, Payment


def build_daily_cash_close(*, tenant, day: date, tz) -> dict:
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()), tz)
    end = start + timedelta(days=1)

    pay_qs = Payment.objects.filter(
        tenant=tenant,
        status=Payment.Status.CAPTURED,
        created_at__gte=start,
        created_at__lt=end,
    )
    pay_sums = pay_qs.aggregate(
        cash_in=Coalesce(
            Sum(
                Case(
                    When(
                        method=Payment.Method.CASH,
                        direction=Payment.Direction.IN,
                        then="amount_cents",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
        cash_out=Coalesce(
            Sum(
                Case(
                    When(
                        method=Payment.Method.CASH,
                        direction=Payment.Direction.OUT,
                        then="amount_cents",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
        card_in=Coalesce(
            Sum(
                Case(
                    When(
                        method=Payment.Method.CARD,
                        direction=Payment.Direction.IN,
                        then="amount_cents",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
        card_out=Coalesce(
            Sum(
                Case(
                    When(
                        method=Payment.Method.CARD,
                        direction=Payment.Direction.OUT,
                        then="amount_cents",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
    )

    adjustment_qs = Adjustment.objects.filter(
        tenant=tenant,
        status=Adjustment.Status.APPLIED,
        created_at__gte=start,
        created_at__lt=end,
    )
    adjustment_sums = adjustment_qs.aggregate(
        adj_in=Coalesce(
            Sum(
                Case(
                    When(
                        direction=Adjustment.Direction.IN,
                        then="amount_cents",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
        adj_out=Coalesce(
            Sum(
                Case(
                    When(
                        direction=Adjustment.Direction.OUT,
                        then="amount_cents",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
    )

    settlement_qs = Order.objects.filter(
        tenant=tenant,
        settled_at__gte=start,
        settled_at__lt=end,
    )
    settlement_sums = settlement_qs.aggregate(
        orders_settled_count=Count("id"),
        settled_total_cents=Coalesce(Sum("settled_total_cents"), 0),
        settled_paid_cents=Coalesce(Sum("settled_paid_cents"), 0),
        settled_change_cents=Coalesce(Sum("settled_change_cents"), 0),
        settled_balance_due_cents=Coalesce(Sum("settled_balance_due_cents"), 0),
    )

    cash_in = int(pay_sums["cash_in"])
    cash_out = int(pay_sums["cash_out"])
    card_in = int(pay_sums["card_in"])
    card_out = int(pay_sums["card_out"])
    adj_in = int(adjustment_sums["adj_in"])
    adj_out = int(adjustment_sums["adj_out"])

    return {
        "date": day.isoformat(),
        "tenant": {"id": tenant.id, "slug": tenant.slug},
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "cash": {
            "in_cents": cash_in,
            "out_cents": cash_out,
            "net_cents": cash_in - cash_out,
        },
        "card": {
            "in_cents": card_in,
            "out_cents": card_out,
            "net_cents": card_in - card_out,
        },
        "adjustments": {
            "in_cents": adj_in,
            "out_cents": adj_out,
            "net_cents": adj_in - adj_out,
        },
        "settlement": {
            "orders_settled_count": int(
                settlement_sums["orders_settled_count"] or 0
            ),
            "settled_total_cents": int(settlement_sums["settled_total_cents"]),
            "settled_paid_cents": int(settlement_sums["settled_paid_cents"]),
            "settled_change_cents": int(settlement_sums["settled_change_cents"]),
            "settled_balance_due_cents": int(
                settlement_sums["settled_balance_due_cents"]
            ),
        },
    }


class DailyCashCloseReportView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        date_str = request.query_params.get("date")

        if date_str:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"date": "Invalid format. Use YYYY-MM-DD."}
                ) from exc
        else:
            day = timezone.localdate()

        tz = timezone.get_current_timezone()
        return Response(build_daily_cash_close(tenant=request.tenant, day=day, tz=tz))


class DailyCashCloseReportRangeView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")

        if not start_str or not end_str:
            raise ValidationError(
                {"range": "Both start and end are required (YYYY-MM-DD)."}
            )

        try:
            start_day = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(
                {"start": "Invalid format. Use YYYY-MM-DD."}
            ) from exc

        try:
            end_day = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError({"end": "Invalid format. Use YYYY-MM-DD."}) from exc

        if end_day < start_day:
            raise ValidationError({"range": "End must be on or after start."})

        tz = timezone.get_current_timezone()
        days = (end_day - start_day).days + 1
        payload = [
            build_daily_cash_close(
                tenant=request.tenant,
                day=start_day + timedelta(days=offset),
                tz=tz,
            )
            for offset in range(days)
        ]

        return Response(payload)


def _csv_rows_for_daily_reports(reports: list[dict]) -> list[list[str]]:
    header = [
        "date",
        "tenant_id",
        "tenant_slug",
        "window_start",
        "window_end",
        "cash_in_cents",
        "cash_out_cents",
        "cash_net_cents",
        "card_in_cents",
        "card_out_cents",
        "card_net_cents",
        "adjustments_in_cents",
        "adjustments_out_cents",
        "adjustments_net_cents",
        "settlement_orders_settled_count",
        "settlement_settled_total_cents",
        "settlement_settled_paid_cents",
        "settlement_settled_change_cents",
        "settlement_settled_balance_due_cents",
    ]
    rows = [header]

    for report in reports:
        rows.append(
            [
                report["date"],
                str(report["tenant"]["id"]),
                report["tenant"]["slug"],
                report["window"]["start"],
                report["window"]["end"],
                str(report["cash"]["in_cents"]),
                str(report["cash"]["out_cents"]),
                str(report["cash"]["net_cents"]),
                str(report["card"]["in_cents"]),
                str(report["card"]["out_cents"]),
                str(report["card"]["net_cents"]),
                str(report["adjustments"]["in_cents"]),
                str(report["adjustments"]["out_cents"]),
                str(report["adjustments"]["net_cents"]),
                str(report["settlement"]["orders_settled_count"]),
                str(report["settlement"]["settled_total_cents"]),
                str(report["settlement"]["settled_paid_cents"]),
                str(report["settlement"]["settled_change_cents"]),
                str(report["settlement"]["settled_balance_due_cents"]),
            ]
        )

    return rows


class DailyCashCloseReportCsvView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        date_str = request.query_params.get("date")
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")
        tz = timezone.get_current_timezone()

        if start_str or end_str:
            if not start_str or not end_str:
                raise ValidationError(
                    {"range": "Both start and end are required (YYYY-MM-DD)."}
                )
            try:
                start_day = datetime.strptime(start_str, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"start": "Invalid format. Use YYYY-MM-DD."}
                ) from exc
            try:
                end_day = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"end": "Invalid format. Use YYYY-MM-DD."}
                ) from exc
            if end_day < start_day:
                raise ValidationError({"range": "End must be on or after start."})
            days = (end_day - start_day).days + 1
            reports = [
                build_daily_cash_close(
                    tenant=request.tenant,
                    day=start_day + timedelta(days=offset),
                    tz=tz,
                )
                for offset in range(days)
            ]
        else:
            if date_str:
                try:
                    day = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError as exc:
                    raise ValidationError(
                        {"date": "Invalid format. Use YYYY-MM-DD."}
                    ) from exc
            else:
                day = timezone.localdate()
            reports = [build_daily_cash_close(tenant=request.tenant, day=day, tz=tz)]

        rows = _csv_rows_for_daily_reports(reports)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerows(rows)
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=daily-cash-close.csv"
        return response


class OpsSummaryReportView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        date_str = request.query_params.get("date")
        if date_str:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"date": "Invalid format. Use YYYY-MM-DD."}
                ) from exc
        else:
            day = timezone.localdate()

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(day, datetime.min.time()), tz)
        end = start + timedelta(days=1)

        base_qs = Order.objects.filter(tenant=request.tenant)
        due_exclude_statuses = ["CANCELLED", "PICKED_UP"]

        orders_due_today = base_qs.filter(
            due_at__gte=start,
            due_at__lt=end,
        ).exclude(status__in=due_exclude_statuses).count()

        orders_overdue = base_qs.filter(
            due_at__lt=start,
        ).exclude(status__in=due_exclude_statuses).count()

        orders_ready = base_qs.filter(status="READY").count()
        orders_completed_unpicked = base_qs.filter(
            status="COMPLETED",
            picked_up_at__isnull=True,
        ).count()
        orders_picked_up_today = base_qs.filter(
            picked_up_at__gte=start,
            picked_up_at__lt=end,
        ).count()
        orders_settled_today = base_qs.filter(
            settled_at__gte=start,
            settled_at__lt=end,
        ).count()

        ready_unpaid_count = base_qs.filter(
            status__in=["READY", "COMPLETED"],
            settled_balance_due_cents__gt=0,
        ).count()

        return Response(
            {
                "date": day.isoformat(),
                "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
                "window": {"start": start.isoformat(), "end": end.isoformat()},
                "counts": {
                    "orders_due_today": orders_due_today,
                    "orders_overdue": orders_overdue,
                    "orders_ready": orders_ready,
                    "orders_ready_unpaid": ready_unpaid_count,
                    "orders_completed_unpicked": orders_completed_unpicked,
                    "orders_picked_up_today": orders_picked_up_today,
                    "orders_settled_today": orders_settled_today,
                },
                "ready_unpaid_mode": "settled_only",
            }
        )


def _classify_cash_out_breakdown(out_payments: list[dict]) -> tuple[dict, list[str]]:
    change_cents = 0
    refund_cents = 0
    other_cents = 0
    classified = False

    for payment in out_payments:
        amount = int(payment["amount_cents"] or 0)
        reference = (payment.get("reference") or "").lower()
        note = (payment.get("note") or "").lower()

        if reference.endswith("-change") or "change" in note:
            change_cents += amount
            classified = True
        elif "refund" in note:
            refund_cents += amount
            classified = True
        else:
            other_cents += amount

    if not classified and (change_cents + refund_cents + other_cents) > 0:
        return (
            {
                "change_paid_out_cents": 0,
                "refunds_cash_out_cents": 0,
                "other_cash_out_cents": change_cents + refund_cents + other_cents,
            },
            [
                "Breakdown unavailable without semantic payment fields; all cash-out recorded as other."
            ],
        )

    return (
        {
            "change_paid_out_cents": change_cents,
            "refunds_cash_out_cents": refund_cents,
            "other_cash_out_cents": other_cents,
        },
        [],
    )


class CashDrawerReportView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        date_str = request.query_params.get("date")
        if date_str:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"date": "Invalid format. Use YYYY-MM-DD."}
                ) from exc
        else:
            day = timezone.localdate()

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(day, datetime.min.time()), tz)
        end = start + timedelta(days=1)

        cash_qs = Payment.objects.filter(
            tenant=request.tenant,
            status=Payment.Status.CAPTURED,
            method=Payment.Method.CASH,
            created_at__gte=start,
            created_at__lt=end,
        )

        cash_in = (
            cash_qs.filter(direction=Payment.Direction.IN)
            .aggregate(s=Coalesce(Sum("amount_cents"), 0))
            .get("s")
        )
        cash_out = (
            cash_qs.filter(direction=Payment.Direction.OUT)
            .aggregate(s=Coalesce(Sum("amount_cents"), 0))
            .get("s")
        )

        out_payments = list(
            cash_qs.filter(direction=Payment.Direction.OUT).values(
                "amount_cents",
                "reference",
                "note",
            )
        )
        breakdown, notes = _classify_cash_out_breakdown(out_payments)

        return Response(
            {
                "date": day.isoformat(),
                "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
                "window": {"start": start.isoformat(), "end": end.isoformat()},
                "cash": {
                    "in_cents": int(cash_in),
                    "out_cents": int(cash_out),
                    "net_cents": int(cash_in) - int(cash_out),
                },
                "breakdown": breakdown,
                "notes": notes,
            }
        )


class RevenueReportView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")
        if not start_str or not end_str:
            raise ValidationError(
                {"range": "Both start and end are required (YYYY-MM-DD)."}
            )

        try:
            start_day = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(
                {"start": "Invalid format. Use YYYY-MM-DD."}
            ) from exc

        try:
            end_day = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(
                {"end": "Invalid format. Use YYYY-MM-DD."}
            ) from exc

        if end_day < start_day:
            raise ValidationError({"range": "End must be on or after start."})

        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(
            datetime.combine(start_day, datetime.min.time()), tz
        )
        end_dt = timezone.make_aware(
            datetime.combine(end_day, datetime.min.time()), tz
        ) + timedelta(days=1)

        settled_rows = (
            Order.objects.filter(
                tenant=request.tenant,
                settled_at__gte=start_dt,
                settled_at__lt=end_dt,
            )
            .annotate(day=TruncDate("settled_at", tzinfo=tz))
            .values("day")
            .annotate(
                orders_settled_count=Count("id"),
                settled_total_cents=Coalesce(Sum("settled_total_cents"), 0),
            )
        )

        settled_by_day = {
            row["day"]: {
                "orders_settled_count": int(row["orders_settled_count"] or 0),
                "settled_total_cents": int(row["settled_total_cents"] or 0),
            }
            for row in settled_rows
        }

        payment_rows = (
            Payment.objects.filter(
                tenant=request.tenant,
                status=Payment.Status.CAPTURED,
                method__in=[Payment.Method.CASH, Payment.Method.CARD],
                created_at__gte=start_dt,
                created_at__lt=end_dt,
            )
            .annotate(day=TruncDate("created_at", tzinfo=tz))
            .values("day", "method")
            .annotate(
                in_cents=Coalesce(
                    Sum(
                        Case(
                            When(direction=Payment.Direction.IN, then="amount_cents"),
                            default=0,
                            output_field=IntegerField(),
                        )
                    ),
                    0,
                ),
                out_cents=Coalesce(
                    Sum(
                        Case(
                            When(direction=Payment.Direction.OUT, then="amount_cents"),
                            default=0,
                            output_field=IntegerField(),
                        )
                    ),
                    0,
                ),
            )
        )

        payment_by_day = {}
        for row in payment_rows:
            day = row["day"]
            method = row["method"]
            in_cents = int(row["in_cents"] or 0)
            out_cents = int(row["out_cents"] or 0)
            entry = payment_by_day.setdefault(
                day, {"cash_net_cents": 0, "card_net_cents": 0}
            )
            net = in_cents - out_cents
            if method == Payment.Method.CASH:
                entry["cash_net_cents"] = net
            elif method == Payment.Method.CARD:
                entry["card_net_cents"] = net

        days = (end_day - start_day).days + 1
        buckets = []
        totals_orders = 0
        totals_settled = 0
        totals_cash = 0
        totals_card = 0

        for offset in range(days):
            day = start_day + timedelta(days=offset)
            settled = settled_by_day.get(day, {})
            orders_count = int(settled.get("orders_settled_count", 0))
            settled_total = int(settled.get("settled_total_cents", 0))
            avg_order = int(settled_total // orders_count) if orders_count else 0
            payment_net = payment_by_day.get(day, {})
            cash_net = int(payment_net.get("cash_net_cents", 0))
            card_net = int(payment_net.get("card_net_cents", 0))

            totals_orders += orders_count
            totals_settled += settled_total
            totals_cash += cash_net
            totals_card += card_net

            buckets.append(
                {
                    "date": day.isoformat(),
                    "orders_settled_count": orders_count,
                    "settled_total_cents": settled_total,
                    "avg_order_value_cents": avg_order,
                    "cash_net_cents": cash_net,
                    "card_net_cents": card_net,
                }
            )

        totals_avg = int(totals_settled // totals_orders) if totals_orders else 0

        return Response(
            {
                "start": start_day.isoformat(),
                "end": end_day.isoformat(),
                "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
                "window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
                "days": buckets,
                "totals": {
                    "orders_settled_count": totals_orders,
                    "settled_total_cents": totals_settled,
                    "avg_order_value_cents": totals_avg,
                    "cash_net_cents": totals_cash,
                    "card_net_cents": totals_card,
                },
            }
        )


class SettlementBreakdownReportView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")
        if not start_str or not end_str:
            raise ValidationError(
                {"range": "Both start and end are required (YYYY-MM-DD)."}
            )

        try:
            start_day = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(
                {"start": "Invalid format. Use YYYY-MM-DD."}
            ) from exc

        try:
            end_day = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(
                {"end": "Invalid format. Use YYYY-MM-DD."}
            ) from exc

        if end_day < start_day:
            raise ValidationError({"range": "End must be on or after start."})

        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(
            datetime.combine(start_day, datetime.min.time()), tz
        )
        end_dt = timezone.make_aware(
            datetime.combine(end_day, datetime.min.time()), tz
        ) + timedelta(days=1)

        settled_qs = Order.objects.filter(
            tenant=request.tenant,
            settled_at__gte=start_dt,
            settled_at__lt=end_dt,
        )
        settled_sums = settled_qs.aggregate(
            subtotal_cents=Coalesce(Sum("subtotal_cents"), 0),
            tax_cents=Coalesce(Sum("tax_cents"), 0),
            total_cents=Coalesce(Sum("settled_total_cents"), 0),
            paid_cents=Coalesce(Sum("settled_paid_cents"), 0),
            change_cents=Coalesce(Sum("settled_change_cents"), 0),
            balance_due_cents=Coalesce(Sum("settled_balance_due_cents"), 0),
        )

        adjustment_sums = Adjustment.objects.filter(
            tenant=request.tenant,
            status=Adjustment.Status.APPLIED,
            created_at__gte=start_dt,
            created_at__lt=end_dt,
        ).aggregate(
            adjustments_in_cents=Coalesce(
                Sum(
                    Case(
                        When(direction=Adjustment.Direction.IN, then="amount_cents"),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),
                0,
            ),
            adjustments_out_cents=Coalesce(
                Sum(
                    Case(
                        When(direction=Adjustment.Direction.OUT, then="amount_cents"),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),
                0,
            ),
        )

        adjustments_in = int(adjustment_sums["adjustments_in_cents"] or 0)
        adjustments_out = int(adjustment_sums["adjustments_out_cents"] or 0)

        return Response(
            {
                "start": start_day.isoformat(),
                "end": end_day.isoformat(),
                "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
                "window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
                "subtotal_cents": int(settled_sums["subtotal_cents"] or 0),
                "tax_cents": int(settled_sums["tax_cents"] or 0),
                "total_cents": int(settled_sums["total_cents"] or 0),
                "adjustments_in_cents": adjustments_in,
                "adjustments_out_cents": adjustments_out,
                "adjustments_net_cents": adjustments_in - adjustments_out,
                "paid_cents": int(settled_sums["paid_cents"] or 0),
                "change_cents": int(settled_sums["change_cents"] or 0),
                "balance_due_cents": int(settled_sums["balance_due_cents"] or 0),
            }
        )


class TopCustomersReportView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")
        if not start_str or not end_str:
            raise ValidationError(
                {"range": "Both start and end are required (YYYY-MM-DD)."}
            )

        try:
            start_day = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(
                {"start": "Invalid format. Use YYYY-MM-DD."}
            ) from exc

        try:
            end_day = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError(
                {"end": "Invalid format. Use YYYY-MM-DD."}
            ) from exc

        if end_day < start_day:
            raise ValidationError({"range": "End must be on or after start."})

        limit = request.query_params.get("limit")
        if limit is None or limit == "":
            limit_value = 20
        else:
            try:
                limit_value = int(limit)
            except ValueError as exc:
                raise ValidationError({"limit": "Must be an integer."}) from exc
            if limit_value <= 0:
                raise ValidationError({"limit": "Must be >= 1."})

        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(
            datetime.combine(start_day, datetime.min.time()), tz
        )
        end_dt = timezone.make_aware(
            datetime.combine(end_day, datetime.min.time()), tz
        ) + timedelta(days=1)

        rows = (
            Order.objects.filter(
                tenant=request.tenant,
                settled_at__gte=start_dt,
                settled_at__lt=end_dt,
            )
            .values("customer_id", "customer__name", "customer__phone")
            .annotate(
                orders_count=Count("id"),
                settled_total_cents=Coalesce(Sum("settled_total_cents"), 0),
                last_seen_at=Max("settled_at"),
            )
            .order_by("-settled_total_cents", "-orders_count", "-last_seen_at")
        )[:limit_value]

        results = [
            {
                "customer": {
                    "id": row["customer_id"],
                    "name": row["customer__name"],
                    "phone": row["customer__phone"],
                },
                "orders_count": int(row["orders_count"] or 0),
                "settled_total_cents": int(row["settled_total_cents"] or 0),
                "last_seen_at": row["last_seen_at"].isoformat()
                if row["last_seen_at"]
                else None,
            }
            for row in rows
        ]

        return Response(
            {
                "start": start_day.isoformat(),
                "end": end_day.isoformat(),
                "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
                "results": results,
            }
        )


def _avg_age_hours(qs, *, end):
    avg_age = qs.aggregate(
        avg=Avg(
            ExpressionWrapper(
                Value(end) - F("created_at"),
                output_field=DurationField(),
            )
        )
    )["avg"]
    if not avg_age:
        return 0.0
    return round(avg_age.total_seconds() / 3600, 2)


class WorkloadReportView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        date_str = request.query_params.get("date")
        if date_str:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"date": "Invalid format. Use YYYY-MM-DD."}
                ) from exc
        else:
            day = timezone.localdate()

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(day, datetime.min.time()), tz)
        end = start + timedelta(days=1)

        base_qs = Order.objects.filter(tenant=request.tenant)
        due_exclude_statuses = ["CANCELLED", "PICKED_UP"]

        due_today_qs = base_qs.filter(
            due_at__gte=start,
            due_at__lt=end,
        ).exclude(status__in=due_exclude_statuses)
        overdue_qs = base_qs.filter(
            due_at__lt=start,
        ).exclude(status__in=due_exclude_statuses)
        ready_unpaid_qs = base_qs.filter(
            status__in=["READY", "COMPLETED"],
            settled_balance_due_cents__gt=0,
        )
        completed_unpicked_qs = base_qs.filter(
            status="COMPLETED",
            picked_up_at__isnull=True,
        )

        return Response(
            {
                "date": day.isoformat(),
                "tenant": {"id": request.tenant.id, "slug": request.tenant.slug},
                "window": {"start": start.isoformat(), "end": end.isoformat()},
                "counts": {
                    "orders_due_today": due_today_qs.count(),
                    "orders_overdue": overdue_qs.count(),
                    "orders_ready_unpaid": ready_unpaid_qs.count(),
                    "orders_completed_unpicked": completed_unpicked_qs.count(),
                },
                "avg_age_hours": {
                    "orders_due_today": _avg_age_hours(due_today_qs, end=end),
                    "orders_overdue": _avg_age_hours(overdue_qs, end=end),
                    "orders_ready_unpaid": _avg_age_hours(ready_unpaid_qs, end=end),
                    "orders_completed_unpicked": _avg_age_hours(
                        completed_unpicked_qs, end=end
                    ),
                },
                "ready_unpaid_mode": "settled_only",
            }
        )


def _parse_list(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [value]


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError({"date": "Invalid format. Use YYYY-MM-DD."}) from exc


def _format_usd(cents: int | None) -> str:
    try:
        return f"${(int(cents or 0) / 100):.2f}"
    except Exception:
        return "$0.00"


def _apply_filter(qs, field: str, op: str, value):
    if value in (None, "") and op not in ("isnull",):
        return qs

    lookup = field
    if op in ("eq", "exact"):
        lookup = field
    elif op == "ne":
        return qs.exclude(**{field: value})
    elif op == "icontains":
        lookup = f"{field}__icontains"
    elif op == "contains":
        lookup = f"{field}__contains"
    elif op == "in":
        lookup = f"{field}__in"
        value = _parse_list(value)
    elif op == "gte":
        lookup = f"{field}__gte"
    elif op == "lte":
        lookup = f"{field}__lte"
    elif op == "gt":
        lookup = f"{field}__gt"
    elif op == "lt":
        lookup = f"{field}__lt"
    elif op == "isnull":
        lookup = f"{field}__isnull"
        value = bool(value) if value is not None else True
    elif op == "date":
        lookup = f"{field}__date"
    elif op == "between":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValidationError({"filters": "between expects [start, end]."})
        start, end = value
        return qs.filter(**{f"{field}__gte": start, f"{field}__lte": end})
    else:
        raise ValidationError({"filters": f"Unsupported op '{op}'."})

    return qs.filter(**{lookup: value})


def _build_item_rows(items_qs, tz, limit: int):
    rows = []
    qs = (
        items_qs.select_related("order", "item", "order__customer")
        .order_by("-order__created_at", "order_id", "id")[:limit]
    )
    for item in qs:
        order = item.order
        customer = order.customer
        order_date = None
        if order.created_at:
            order_date = timezone.localtime(order.created_at, tz).date().isoformat()

        rows.append(
            {
                "order_id": order.id,
                "order_status": order.status,
                "order_date": order_date,
                "customer_id": order.customer_id,
                "customer_name": getattr(customer, "name", None) if customer else None,
                "customer_phone": getattr(customer, "phone", None) if customer else None,
                "item_id": item.item_id,
                "item_name": getattr(item.item, "name", None),
                "item_sku": getattr(item.item, "sku", None),
                "quantity": int(item.quantity or 0),
                "unit_price_cents": int(item.unit_price_cents or 0),
                "line_total_cents": int(item.line_total_cents or 0),
                "order_total_cents": int(order.total_cents or 0),
            }
        )
    return rows


def _csv_response(rows, filename: str):
    output = io.StringIO()
    fieldnames = [
        "order_id",
        "order_status",
        "order_date",
        "customer_id",
        "customer_name",
        "customer_phone",
        "item_id",
        "item_name",
        "item_sku",
        "quantity",
        "unit_price_cents",
        "line_total_cents",
        "order_total_cents",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    resp = HttpResponse(output.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def _pdf_response(rows, summary: dict, filters: dict, filename: str):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    def _truncate(value: str, max_len: int) -> str:
        if not value:
            return "-"
        value = str(value)
        return value if len(value) <= max_len else f"{value[: max_len - 1]}…"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title="Order Items Report",
    )
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Report: Order Items", styles["Title"]))
    elements.append(Paragraph(f"Generated: {timezone.now().isoformat()}", styles["Normal"]))
    if filters:
        elements.append(Paragraph(f"Filters: {filters}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Summary", styles["Heading2"]))
    elements.append(Paragraph(f"Orders: {summary.get('orders_count', 0)}", styles["Normal"]))
    elements.append(
        Paragraph(
            f"Order Total: {_format_usd(summary.get('orders_total_cents'))}",
            styles["Normal"],
        )
    )
    elements.append(
        Paragraph(
            f"Items Qty: {summary.get('items_quantity', 0)}",
            styles["Normal"],
        )
    )
    elements.append(
        Paragraph(
            f"Items Revenue: {_format_usd(summary.get('items_revenue_cents'))}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    # Build table data with customer subtotals
    table_rows = [["Date", "Order #", "Customer", "Item", "Qty", "Line Total"]]
    subtotal_rows = []

    sorted_rows = sorted(
        rows,
        key=lambda r: (
            (r.get("customer_name") or "").lower(),
            r.get("order_date") or "",
            r.get("order_id") or 0,
        ),
    )

    current_customer = None
    customer_qty = 0
    customer_total = 0
    grand_qty = 0
    grand_total = 0

    for row in sorted_rows:
        customer = row.get("customer_name") or "Unknown"
        if current_customer is None:
            current_customer = customer
        if customer != current_customer:
            subtotal_rows.append(len(table_rows))
            table_rows.append(
                ["", "", f"{current_customer} total", "", str(customer_qty), _format_usd(customer_total)]
            )
            customer_qty = 0
            customer_total = 0
            current_customer = customer

        qty = int(row.get("quantity") or 0)
        line_total = int(row.get("line_total_cents") or 0)
        customer_qty += qty
        customer_total += line_total
        grand_qty += qty
        grand_total += line_total

        table_rows.append(
            [
                (row.get("order_date") or "-")[:10],
                str(row.get("order_id") or "-"),
                _truncate(customer, 22),
                _truncate(row.get("item_name") or "-", 22),
                str(qty),
                _format_usd(line_total),
            ]
        )

    if current_customer is not None:
        subtotal_rows.append(len(table_rows))
        table_rows.append(
            ["", "", f"{current_customer} total", "", str(customer_qty), _format_usd(customer_total)]
        )

    table_rows.append(["", "", "Grand Total", "", str(grand_qty), _format_usd(grand_total)])
    subtotal_rows.append(len(table_rows) - 1)

    table = Table(
        table_rows,
        colWidths=[70, 55, 140, 140, 40, 70],
        repeatRows=1,
        hAlign="LEFT",
    )
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (4, 1), (5, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
    )
    for row_idx in subtotal_rows:
        table_style.add("FONTNAME", (0, row_idx), (-1, row_idx), "Helvetica-Bold")
        table_style.add("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#fafafa"))

    table.setStyle(table_style)
    elements.append(table)
    doc.build(elements)

    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


class ReportQueryView(APIView):
    """
    POST /api/reports/query/
    Flexible reporting endpoint for AI-driven queries.
    """
    permission_classes = [IsTenantMember]

    def post(self, request):
        data = request.data or {}
        tenant = request.tenant
        tz = timezone.get_current_timezone()

        output = str(data.get("output") or "summary").lower().strip()
        if output not in ("summary", "csv", "pdf"):
            raise ValidationError({"output": "Use one of: summary, csv, pdf."})

        date_start = _parse_date(data.get("date_start"))
        date_end = _parse_date(data.get("date_end"))
        if date_start and not date_end:
            date_end = date_start
        if date_end and not date_start:
            date_start = date_end

        orders_qs = Order.objects.filter(tenant=tenant)
        payments_qs = Payment.objects.filter(tenant=tenant)

        if date_start and date_end:
            start = timezone.make_aware(datetime.combine(date_start, datetime.min.time()), tz)
            end = timezone.make_aware(datetime.combine(date_end, datetime.min.time()), tz) + timedelta(days=1)
            orders_qs = orders_qs.filter(created_at__gte=start, created_at__lt=end)
            payments_qs = payments_qs.filter(created_at__gte=start, created_at__lt=end)

        status_list = _parse_list(data.get("status"))
        exclude_status_list = _parse_list(data.get("exclude_status"))
        include_cancelled = data.get("include_cancelled", False) in (
            True,
            "true",
            "True",
            "1",
            "yes",
        )
        if status_list:
            orders_qs = orders_qs.filter(status__in=status_list)
        elif not include_cancelled:
            orders_qs = orders_qs.exclude(status="CANCELLED")

        if exclude_status_list:
            orders_qs = orders_qs.exclude(status__in=exclude_status_list)

        customer_id = data.get("customer_id")
        if customer_id:
            orders_qs = orders_qs.filter(customer_id=customer_id)
            payments_qs = payments_qs.filter(order__customer_id=customer_id)

        customer_name = data.get("customer_name")
        if customer_name:
            orders_qs = orders_qs.filter(customer__name__icontains=customer_name)

        customer_phone = data.get("customer_phone")
        if customer_phone:
            orders_qs = orders_qs.filter(customer__phone__icontains=customer_phone)

        customer_email = data.get("customer_email")
        if customer_email:
            orders_qs = orders_qs.filter(customer__email__icontains=customer_email)

        item_contains = data.get("item_contains")
        item_ids = _parse_list(data.get("item_ids"))
        if item_contains:
            orders_qs = orders_qs.filter(items__item__name__icontains=item_contains)
            payments_qs = payments_qs.filter(order__items__item__name__icontains=item_contains)
        if item_ids:
            orders_qs = orders_qs.filter(items__item_id__in=item_ids)
            payments_qs = payments_qs.filter(order__items__item_id__in=item_ids)

        min_total = data.get("min_total_cents")
        max_total = data.get("max_total_cents")
        if min_total is not None:
            orders_qs = orders_qs.filter(total_cents__gte=int(min_total))
        if max_total is not None:
            orders_qs = orders_qs.filter(total_cents__lte=int(max_total))

        payment_methods = _parse_list(data.get("payment_method"))
        if payment_methods:
            payments_qs = payments_qs.filter(method__in=payment_methods)

        payment_status = _parse_list(data.get("payment_status")) or [Payment.Status.CAPTURED]
        payments_qs = payments_qs.filter(status__in=payment_status)

        payment_directions = _parse_list(data.get("payment_direction"))
        if payment_directions:
            payments_qs = payments_qs.filter(direction__in=payment_directions)

        extra_filters = data.get("filters") or []
        item_filters = []
        item_filter_map_items = {}
        if extra_filters:
            if not isinstance(extra_filters, list):
                raise ValidationError({"filters": "Expected a list of filter objects."})

            order_filter_map = {
                "order.id": "id",
                "order.status": "status",
                "order.total_cents": "total_cents",
                "order.subtotal_cents": "subtotal_cents",
                "order.tax_cents": "tax_cents",
                "order.paid_cents": "paid_cents",
                "order.created_at": "created_at",
                "order.due_at": "due_at",
                "order.received_at": "received_at",
                "order.in_progress_at": "in_progress_at",
                "order.ready_at": "ready_at",
                "order.completed_at": "completed_at",
                "order.cancelled_at": "cancelled_at",
                "order.picked_up_at": "picked_up_at",
                "customer.id": "customer_id",
                "customer.name": "customer__name",
                "customer.phone": "customer__phone",
                "customer.email": "customer__email",
            }
            item_filter_map_orders = {
                "item.id": "items__item_id",
                "item.name": "items__item__name",
                "item.sku": "items__item__sku",
            }
            item_filter_map_items = {
                "item.id": "item_id",
                "item.name": "item__name",
                "item.sku": "item__sku",
            }
            payment_filter_map = {
                "payment.method": "method",
                "payment.status": "status",
                "payment.direction": "direction",
                "payment.amount_cents": "amount_cents",
                "payment.reference": "reference",
                "payment.created_at": "created_at",
            }

            for filt in extra_filters:
                if not isinstance(filt, dict):
                    continue
                field = filt.get("field")
                op = str(filt.get("op") or "eq").lower()
                value = filt.get("value")
                if field in order_filter_map:
                    orders_qs = _apply_filter(
                        orders_qs, order_filter_map[field], op, value
                    )
                elif field in item_filter_map_orders:
                    orders_qs = _apply_filter(
                        orders_qs, item_filter_map_orders[field], op, value
                    )
                    item_filters.append((field, op, value))
                elif field in payment_filter_map:
                    payments_qs = _apply_filter(
                        payments_qs, payment_filter_map[field], op, value
                    )
                    orders_qs = orders_qs.filter(payments__in=payments_qs)
                else:
                    raise ValidationError({"filters": f"Unsupported field '{field}'."})

        orders_qs = orders_qs.distinct()
        payments_qs = payments_qs.filter(order__in=orders_qs)

        orders_count = orders_qs.count()
        orders_total_cents = int(
            orders_qs.aggregate(s=Coalesce(Sum("total_cents"), 0)).get("s") or 0
        )
        avg_ticket_cents = int(orders_total_cents / orders_count) if orders_count else 0

        items_qs = OrderItem.objects.filter(order__in=orders_qs)
        if item_contains:
            items_qs = items_qs.filter(item__name__icontains=item_contains)
        if item_ids:
            items_qs = items_qs.filter(item_id__in=item_ids)
        if item_filters:
            for field, op, value in item_filters:
                items_qs = _apply_filter(
                    items_qs, item_filter_map_items[field], op, value
                )

        items_quantity = int(
            items_qs.aggregate(s=Coalesce(Sum("quantity"), 0)).get("s") or 0
        )
        items_revenue_cents = int(
            items_qs.aggregate(s=Coalesce(Sum("line_total_cents"), 0)).get("s") or 0
        )

        payment_in_cents = int(
            payments_qs.filter(direction=Payment.Direction.IN).aggregate(
                s=Coalesce(Sum("amount_cents"), 0)
            )["s"]
            or 0
        )
        payment_out_cents = int(
            payments_qs.filter(direction=Payment.Direction.OUT).aggregate(
                s=Coalesce(Sum("amount_cents"), 0)
            )["s"]
            or 0
        )

        method_rows = (
            payments_qs.values("method")
            .annotate(
                count=Count("id"),
                in_cents=Coalesce(
                    Sum(
                        Case(
                            When(direction=Payment.Direction.IN, then="amount_cents"),
                            default=0,
                            output_field=IntegerField(),
                        )
                    ),
                    0,
                ),
                out_cents=Coalesce(
                    Sum(
                        Case(
                            When(direction=Payment.Direction.OUT, then="amount_cents"),
                            default=0,
                            output_field=IntegerField(),
                        )
                    ),
                    0,
                ),
            )
            .order_by("method")
        )

        by_method = [
            {
                "method": row["method"],
                "count": int(row["count"] or 0),
                "in_cents": int(row["in_cents"] or 0),
                "out_cents": int(row["out_cents"] or 0),
                "net_cents": int(row["in_cents"] or 0) - int(row["out_cents"] or 0),
            }
            for row in method_rows
        ]

        by_item = list(
            items_qs.values("item_id", "item__name")
            .annotate(
                quantity=Coalesce(Sum("quantity"), 0),
                revenue_cents=Coalesce(Sum("line_total_cents"), 0),
            )
            .order_by("-revenue_cents")[:50]
        )

        include_orders = data.get("include_orders", False) in (
            True,
            "true",
            "True",
            "1",
            "yes",
        )
        preview_limit = int(data.get("limit", 50))
        preview_limit = max(1, min(preview_limit, 200))
        export_limit = int(data.get("export_limit", data.get("limit", 2000)))
        export_limit = max(1, min(export_limit, 5000))

        orders_preview = []
        if include_orders:
            for order in orders_qs.select_related("customer").order_by("-created_at")[
                :preview_limit
            ]:
                orders_preview.append(
                    {
                        "id": order.id,
                        "status": order.status,
                        "created_at": order.created_at.isoformat() if order.created_at else None,
                        "customer": {
                            "id": order.customer_id,
                            "name": getattr(order.customer, "name", None),
                        },
                        "total_cents": int(order.total_cents or 0),
                    }
                )

        filters_payload = {
            "date_start": str(date_start) if date_start else None,
            "date_end": str(date_end) if date_end else None,
            "status": status_list,
            "exclude_status": exclude_status_list,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "item_contains": item_contains,
            "item_ids": item_ids,
            "payment_method": payment_methods,
            "payment_status": payment_status,
            "payment_direction": payment_directions,
            "include_cancelled": include_cancelled,
            "extra_filters": extra_filters,
        }

        summary_payload = {
            "orders_count": orders_count,
            "orders_total_cents": orders_total_cents,
            "avg_ticket_cents": avg_ticket_cents,
            "items_quantity": items_quantity,
            "items_revenue_cents": items_revenue_cents,
            "payments": {
                "in_cents": payment_in_cents,
                "out_cents": payment_out_cents,
                "net_cents": payment_in_cents - payment_out_cents,
                "by_method": by_method,
            },
        }

        if output in ("csv", "pdf"):
            rows = _build_item_rows(items_qs, tz, export_limit)
            filename_base = "report-items"
            if date_start and date_end:
                filename_base = f"report-items-{date_start}-{date_end}"
            filename = f"{filename_base}.{output}"
            if output == "csv":
                return _csv_response(rows, filename)
            return _pdf_response(rows, summary_payload, filters_payload, filename)

        return Response(
            {
                "filters": filters_payload,
                "summary": summary_payload,
                "items": {"by_item": by_item},
                "orders": orders_preview,
            }
        )
