from datetime import datetime, timedelta

from django.utils import timezone


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
