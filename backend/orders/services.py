# orders/services.py
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict

from django.db import transaction
from django.db.models import Sum

from .models import Order


def recalc_order_totals(order: Order, tax_rate: float = 0.08) -> None:
    """
    Recalculate and persist order subtotal/tax/total/paid using captured payments.
    NOTE: Do not change money math here in Step 4 unless a test forces it.
    """
    from payments.models import Payment

    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .select_related("tenant")
            .get(pk=order.pk)
        )

        items = order.items.all()
        subtotal = sum(i.line_total_cents for i in items)
        if getattr(order.tenant, "collects_tax", True) is False:
            tax = 0
        else:
            tenant_bps = getattr(order.tenant, "tax_rate_bps", None)
            rate = tax_rate if tenant_bps is None else (tenant_bps / 10000)
            tax = int(round(subtotal * rate))
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

        order.paid_cents = max(int(captured_in - captured_out), 0)

        order.save(
            update_fields=[
                "subtotal_cents",
                "tax_cents",
                "total_cents",
                "paid_cents",
            ]
        )


def receipt_financials_for_order(order: Order) -> Dict[str, int]:
    """
    Derive receipt financial fields using the receipt serializer path.
    """
    from .serializers import OrderReceiptSerializer

    ser = OrderReceiptSerializer(order)
    data = {
        "net_paid_cents": ser.get_net_paid_cents(order),
        "balance_due_cents": ser.get_balance_due_cents(order),
        "change_due_cents": ser.get_change_due_cents(order),
    }
    return {
        "net_paid_cents": int(data.get("net_paid_cents") or 0),
        "balance_due_cents": int(data.get("balance_due_cents") or 0),
        "change_due_cents": int(data.get("change_due_cents") or 0),
    }


# --- Receipt presenter + PDF rendering (Step 4.1) ----------------------------

@dataclass(frozen=True)
class ReceiptPresenter:
    """
    Single source of truth receipt view model.
    Delegates to OrderReceiptSerializer (no money math here).
    """
    order: Order

    def build(self) -> Dict[str, Any]:
        # Import locally to avoid any chance of circular imports later.
        from .serializers import OrderReceiptSerializer
        return OrderReceiptSerializer(self.order).data


def render_receipt_pdf(receipt: Dict[str, Any]) -> bytes:
    """
    Render a receipt PDF from the presenter output.
    NO money math here. Only formatting.

    Expects OrderReceiptSerializer output shape:
      - top-level: id, status, created_at, settled_at, subtotal_cents, tax_cents,
                   total_cents, paid_cents, net_paid_cents, balance_due_cents, change_due_cents
      - customer: {name, phone, email}
      - items: [{quantity, item_name, sku, unit_price_cents, line_total_cents}]
      - payments: [{method, status, direction, amount_cents, ...}]
      - adjustments: [{kind, status, direction, amount_cents, ...}]
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    _, height = letter

    x = 40
    y = height - 40
    line_h = 14

    def _usd(cents: Any) -> str:
        try:
            return f"${int(cents) / 100:.2f}"
        except Exception:
            return "$0.00"

    def draw(line: str) -> None:
        nonlocal y
        c.drawString(x, y, (line or "")[:110])
        y -= line_h
        if y < 50:
            c.showPage()
            y = height - 40

    # Header
    draw("Dry Cleaner")
    draw(f"Order #{receipt.get('id')}")
    draw(f"Created: {receipt.get('created_at') or ''}")
    draw(f"Status: {receipt.get('status') or ''}")
    draw(f"Settled: {'YES' if receipt.get('settled_at') else 'NO'}")
    draw("")

    # Customer
    customer = receipt.get("customer") or {}
    if customer:
        if customer.get("name"):
            draw(f"Customer: {customer.get('name')}")
        if customer.get("phone"):
            draw(f"Phone: {customer.get('phone')}")
        if customer.get("email"):
            draw(f"Email: {customer.get('email')}")
        draw("")

    # Items
    draw("Items:")
    for it in (receipt.get("items") or []):
        qty = it.get("quantity", 1)
        name = it.get("item_name") or "Item"
        sku = it.get("sku") or ""
        unit = _usd(it.get("unit_price_cents"))
        line_total = _usd(it.get("line_total_cents"))
        label = f"{name}" + (f" ({sku})" if sku else "")
        draw(f"- {qty} x {label} @ {unit} = {line_total}")

    draw("")

    # Adjustments (only APPLIED, for operator clarity)
    adjustments = receipt.get("adjustments") or []
    applied_any = False
    for a in adjustments:
        if a.get("status") != "APPLIED":
            continue
        if not applied_any:
            draw("Adjustments:")
            applied_any = True
        amt = _usd(a.get("amount_cents"))
        direction = (a.get("direction") or "").upper()
        kind = a.get("kind") or "ADJUSTMENT"
        sign = "+" if direction == "IN" else "-"
        draw(f"  * {kind}: {sign}{amt}")
    if applied_any:
        draw("")

    # Totals (top-level serializer fields)
    draw(f"Subtotal: {_usd(receipt.get('subtotal_cents'))}")
    draw(f"Tax: {_usd(receipt.get('tax_cents'))}")
    draw(f"Total: {_usd(receipt.get('total_cents'))}")
    draw(f"Paid: {_usd(receipt.get('paid_cents'))}")
    draw(f"Net Paid (incl adj): {_usd(receipt.get('net_paid_cents'))}")
    draw(f"Balance Due: {_usd(receipt.get('balance_due_cents'))}")
    draw(f"Change Due: {_usd(receipt.get('change_due_cents'))}")

    # Payments
    payments = receipt.get("payments") or []
    if payments:
        draw("")
        draw("Payments:")
        for p in payments:
            amt = _usd(p.get("amount_cents"))
            direction = (p.get("direction") or "").upper()
            method = p.get("method") or ""
            status = p.get("status") or ""
            sign = "+" if direction == "IN" else "-"
            draw(f"  * {method} {status}: {sign}{amt}")

    c.showPage()
    c.save()
    return buf.getvalue()
