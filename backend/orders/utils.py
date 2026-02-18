from datetime import datetime, timedelta
import re

from django.utils import timezone


ORDER_SKU_PREFIX = "ORD"
ORDER_SKU_PADDING = 8
ORDER_SKU_RE = re.compile(r"^ORD-(\d+)$", re.IGNORECASE)


def default_due_at_for_tenant(tenant, now=None):
    """
    Compute default pickup promise using tenant settings:
    localdate(now) + default_turnaround_days at (default_ready_hour:default_ready_minute).
    """
    if now is None:
        now = timezone.now()

    due_day = timezone.localdate(
        now) + timedelta(days=int(tenant.default_turnaround_days or 0))

    hour = int(getattr(tenant, "default_ready_hour", 17) or 17)
    minute = int(getattr(tenant, "default_ready_minute", 0) or 0)

    tz = timezone.get_current_timezone()
    return timezone.make_aware(
        datetime(due_day.year, due_day.month, due_day.day, hour, minute, 0),
        tz
    )


def order_sku_for_order_id(order_id: int) -> str:
    return f"{ORDER_SKU_PREFIX}-{int(order_id):0{ORDER_SKU_PADDING}d}"


def order_sku_for_order(order) -> str:
    return order_sku_for_order_id(order.id)


def order_id_from_sku(value: str) -> int | None:
    if not value:
        return None
    match = ORDER_SKU_RE.match(value.strip())
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None
