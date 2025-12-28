# orders/services.py
from django.db import transaction
from django.db.models import Sum
from .models import Order


def recalc_order_totals(order: Order, tax_rate=0.08):
    """
    Recalculate subtotal/tax/total + paid_cents derived from payments.
    Safe under concurrency (locks the order row).
    """
    from payments.models import Payment  # local import avoids circulars

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)

        items = order.items.all()
        subtotal = sum(i.line_total_cents for i in items)
        tax = int(round(subtotal * tax_rate))
        total = subtotal + tax

        order.subtotal_cents = subtotal
        order.tax_cents = tax
        order.total_cents = total

        captured_in = (
            order.payments.filter(
                status=Payment.Status.CAPTURED,
                direction=Payment.Direction.IN,
            ).aggregate(s=Sum("amount_cents"))["s"]
            or 0
        )
        captured_out = (
            order.payments.filter(
                status=Payment.Status.CAPTURED,
                direction=Payment.Direction.OUT,
            ).aggregate(s=Sum("amount_cents"))["s"]
            or 0
        )

        order.paid_cents = int(captured_in - captured_out)

        order.save(update_fields=[
            "subtotal_cents",
            "tax_cents",
            "total_cents",
            "paid_cents",
        ])
