# Financial Invariants (Accounting Core)

This document defines the accounting rules that must remain true across the codebase. These rules are enforced by tests and must not be changed unless a test forces a change and the change is explicitly justified.

Scope: orders, receipts, payments, adjustments, and settlement.

---

## Goals

- Every money number shown to an operator must be explainable from persisted rows.
- Receipts must be reprint-safe: after settlement they must not change.
- All money flows must be append-only (create rows, do not mutate history).
- The system must support refunds and change-outs explicitly as OUT direction events.

---

## Money Fields and Meaning

All monetary values are stored as integer cents.

Order fields:
- subtotal_cents: sum of item line totals
- tax_cents: tax derived from subtotal
- total_cents: subtotal_cents + tax_cents
- paid_cents: net captured payments (IN minus OUT), clamped to >= 0
- settled_at: timestamp when order is financially locked
- settled_total_cents: snapshot of total at settlement
- settled_paid_cents: snapshot of paid at settlement
- settled_change_cents: snapshot of change at settlement
- settled_balance_due_cents: snapshot of balance due at settlement

Payment fields:
- status: only CAPTURED affects totals
- direction: IN increases paid, OUT decreases paid (refund or change-out)
- amount_cents: positive integer amount
- reference: used for idempotency

Adjustment fields:
- status: only APPLIED affects receipt net paid
- direction: IN increases net paid, OUT decreases net paid
- amount_cents: positive integer amount

---

## Single Source of Truth for Totals

recalc_order_totals(order) is the only place that recalculates:
- subtotal_cents
- tax_cents
- total_cents
- paid_cents

Rules:
- recalc_order_totals uses transaction.atomic and select_for_update on the Order row.
- paid_cents is derived from CAPTURED payments only.
- paid_cents = max(captured_in - captured_out, 0)
- adjustments are not persisted into paid_cents; they are applied at receipt level only.

---

## Receipt Computation Rules

Receipts must be derived from a single receipt view model.

Receipt presenter:
- ReceiptPresenter is the single source of truth for receipt data.
- JSON receipts and PDF receipts must both originate from the presenter output.
- The PDF renderer must not introduce any money math.

Receipt net paid:
- net_paid_cents = paid_cents + adjustments_net_cents
- adjustments_net_cents includes only APPLIED adjustments:
  - direction IN adds amount
  - direction OUT subtracts amount

Receipt balance due:
- balance_due_cents = max(total - net_paid_cents, 0)

Receipt change due:
- If there exists a CAPTURED OUT payment for the order, change_due_cents must be 0.
- Otherwise change_due_cents = max(net_paid_cents - total, 0)

---

## Settlement (Financial Lock)

Settlement is the financial finalization step.

Rules:
- Only COMPLETED orders can be settled.
- Settlement is idempotent.
- Settlement requires no balance due.

On settlement, the following snapshot fields are written exactly once:
- settled_at
- settled_total_cents
- settled_paid_cents
- settled_change_cents
- settled_balance_due_cents

After settlement:
- No new payments may be created.
- No cash-out may be created.
- Receipt rendering must use snapshot totals.

---

## Idempotency Requirements

Payments:
- Payment creation must be idempotent by reference.
- Duplicate references must return the existing row.

Settlement:
- Calling settle twice returns the existing settlement receipt.

---

## What Is Allowed vs Not Allowed

Allowed:
- Create new Payment rows.
- Create OUT payments for refunds or change.
- Create Adjustment rows.
- Recompute totals via recalc_order_totals.

Not allowed:
- Mutating existing payment or adjustment history.
- Introducing money math outside the defined paths.
- Making PDF output differ from receipt presenter data.

---

## Testing Expectations

Tests enforce:
- settlement stability
- tenant isolation
- idempotency
- receipt correctness

Any change to financial logic must update tests and document the reason.

