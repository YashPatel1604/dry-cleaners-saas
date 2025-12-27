from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum

from .models import OrderItem, Order

TAX_RATE = 0.08  # simple default (we’ll make tenant-configurable later)


def recalc_order_totals(order: Order):
    subtotal = order.items.aggregate(s=Sum("line_total_cents"))["s"] or 0
    tax = int(round(subtotal * TAX_RATE))
    total = subtotal + tax

    Order.objects.filter(id=order.id).update(
        subtotal_cents=subtotal,
        tax_cents=tax,
        total_cents=total,
    )


@receiver(post_save, sender=OrderItem)
def orderitem_saved(sender, instance: OrderItem, **kwargs):
    recalc_order_totals(instance.order)


@receiver(post_delete, sender=OrderItem)
def orderitem_deleted(sender, instance: OrderItem, **kwargs):
    recalc_order_totals(instance.order)
