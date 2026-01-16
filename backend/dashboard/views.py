from __future__ import annotations

from datetime import timedelta, date

from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from tenants.permissions import IsTenantMember
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from payments.models import Payment


def cents_to_amount_str(cents: int | None) -> str:
    if cents is None:
        cents = 0
    dollars = cents // 100
    remainder = cents % 100
    return f"{dollars}.{remainder:02d}"


def parse_range_days(raw: str | None) -> int:
    if raw in (None, "", "7d"):
        return 7
    if raw == "30d":
        return 30
    return 7


class DashboardSummaryView(APIView):
    permission_classes = [IsTenantMember]
    OVERDUE_DAYS = 3

    def get(self, request):
        tenant = request.tenant
        now = timezone.now()
        today = timezone.localdate(now)

        orders_qs = Order.objects.filter(tenant=tenant)

        orders_today = orders_qs.filter(created_at__date=today).count()

        orders_value_today_cents = (
            orders_qs.filter(created_at__date=today)
            .aggregate(s=Sum("total_cents"))
            .get("s") or 0
        )

        pay_qs = Payment.objects.filter(tenant=tenant, created_at__date=today)

        captured_in = (
            pay_qs.filter(status=Payment.Status.CAPTURED,
                          direction=Payment.Direction.IN)
            .aggregate(s=Sum("amount_cents")).get("s") or 0
        )
        captured_out = (
            pay_qs.filter(status=Payment.Status.CAPTURED,
                          direction=Payment.Direction.OUT)
            .aggregate(s=Sum("amount_cents")).get("s") or 0
        )
        collected_today_cents = int(captured_in) - int(captured_out)

        in_progress = orders_qs.filter(status="IN_PROGRESS").count()
        ready = orders_qs.filter(status="READY").count()

        cutoff = now - timedelta(days=self.OVERDUE_DAYS)
        overdue = orders_qs.filter(
            status="READY",
            ready_at__isnull=False,
            ready_at__lte=cutoff,
        ).count()

        return Response({
            "orders_today": orders_today,
            "orders_value_today": cents_to_amount_str(orders_value_today_cents),
            "collected_today": cents_to_amount_str(collected_today_cents),
            "in_progress": in_progress,
            "ready": ready,
            "overdue": overdue,
        })


class DashboardRevenueView(APIView):
    """
    GET /api/dashboard/revenue/?range=7d|30d
    Returns daily buckets with zero-filled missing dates.
    """
    permission_classes = [IsTenantMember]

    def get(self, request):
        tenant = request.tenant
        now = timezone.now()
        today = timezone.localdate(now)

        days = parse_range_days(request.query_params.get("range"))
        start_day: date = today - timedelta(days=days - 1)

        # Orders per day: count + booked value
        order_rows = (
            Order.objects.filter(
                tenant=tenant,
                created_at__date__gte=start_day,
                created_at__date__lte=today,
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                orders=Count("id"),
                orders_value_cents=Sum("total_cents"),
            )
            .order_by("day")
        )

        orders_by_day: dict[date, dict] = {}
        for r in order_rows:
            d = r["day"]
            orders_by_day[d] = {
                "orders": int(r["orders"] or 0),
                "orders_value_cents": int(r["orders_value_cents"] or 0),
            }

        # Payments per day: net collected (captured IN - OUT)
        pay_rows = (
            Payment.objects.filter(
                tenant=tenant,
                created_at__date__gte=start_day,
                created_at__date__lte=today,
                status=Payment.Status.CAPTURED,
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                in_cents=Sum("amount_cents", filter=Q(
                    direction=Payment.Direction.IN)),
                out_cents=Sum("amount_cents", filter=Q(
                    direction=Payment.Direction.OUT)),
            )
            .order_by("day")
        )

        collected_by_day: dict[date, int] = {}
        for r in pay_rows:
            d = r["day"]
            inc = int(r["in_cents"] or 0)
            outc = int(r["out_cents"] or 0)
            collected_by_day[d] = inc - outc

        # Fill gaps
        out = []
        for i in range(days):
            d = start_day + timedelta(days=i)
            ob = orders_by_day.get(d, {})
            ov = int(ob.get("orders_value_cents", 0))
            oc = int(ob.get("orders", 0))
            cc = int(collected_by_day.get(d, 0))

            out.append({
                "date": d.isoformat(),
                "orders": oc,
                "orders_value": cents_to_amount_str(ov),
                "collected": cents_to_amount_str(cc),
            })

        return Response(out)


class DashboardOrdersByStatusView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        tenant = request.tenant
        rows = (
            Order.objects.filter(tenant=tenant)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        return Response([{"status": r["status"], "count": r["count"]} for r in rows])
