from .models import Order


def recalc_order_totals(order: Order, tax_rate=0.08):
    items = order.items.all()

    subtotal = sum(i.line_total_cents for i in items)
    tax = int(round(subtotal * tax_rate))
    total = subtotal + tax

    order.subtotal_cents = subtotal
    order.tax_cents = tax
    order.total_cents = total

    order.save(update_fields=[
        "subtotal_cents",
        "tax_cents",
        "total_cents",
    ])
