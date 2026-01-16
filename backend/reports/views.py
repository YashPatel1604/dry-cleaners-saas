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

from orders.models import Order
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
