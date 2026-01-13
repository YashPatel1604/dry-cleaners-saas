Financial Invariants (Accounting Core)

This document defines the accounting rules that must remain true across the codebase. These rules are enforced by tests and must not be changed unless a test forces a change and the change is explicitly justified.

Scope: orders, receipts, payments, adjustments, and settlement.

Goals

Every money number shown to an operator must be explainable from persisted rows.

Receipts must be reprint-safe: after settlement they must not change.

All money flows must be append-only (create rows, do not mutate history).

The system must support refunds/change-outs explicitly as OUT direction events.

Money Fields and Meaning

All monetary values are stored as integer cents.

Order fields:

subtotal_cents: sum of item line totals

tax_cents: tax derived from subtotal

total_cents: subtotal_cents + tax_cents

paid_cents: net captured payments (IN minus OUT), clamped to >= 0

settled_at: timestamp when order is financially locked

settled_total_cents: snapshot of total at settlement

settled_paid_cents: snapshot of paid at settlement

settled_change_cents: snapshot of change at settlement

settled_balance_due_cents: snapshot of balance due at settlement

Payment fields:

status: only CAPTURED affects totals

direction: IN increases paid, OUT decreases paid (refund/change-out)

amount_cents: positive integer amount

reference: used for idempotency

Adjustment fields:

status: only APPLIED affects receipt net paid

direction: IN increases net paid, OUT decreases net paid

amount_cents: positive integer amount

Single Source of Truth for Totals

recalc_order_totals(order) is the only place that recalculates:

subtotal_cents

tax_cents

total_cents

paid_cents

No other code should compute or “fix” these fields independently.

Rules:

recalc_order_totals uses transaction.atomic and select_for_update on the Order row.

paid_cents is derived from CAPTURED payments only.

paid_cents = max(captured_in - captured_out, 0)

adjustments are not persisted into paid_cents; they are applied at receipt/presenter level only.

Receipt Computation Rules

Receipts must be derived from a single receipt view model.

Receipt presenter:

ReceiptPresenter is the single source of truth for receipt data.

JSON receipts and PDF receipts must both originate from the presenter output.

The PDF renderer must not introduce any money math.

Receipt net paid:

net_paid_cents = paid_cents + adjustments_net_cents

adjustments_net_cents includes only APPLIED adjustments:

direction IN adds amount

direction OUT subtracts amount

Receipt balance due:

balance_due_cents = max(total - net_paid_cents, 0)

Receipt change due:

If there exists a CAPTURED OUT payment for the order, change_due_cents must be 0 (change already recorded as a drawer event).

Otherwise change_due_cents = max(net_paid_cents - total, 0)

Settlement (Financial Lock)

Settlement is the financial “finalization” step.

Rules:

Only COMPLETED orders can be settled.

Settlement is idempotent: if settled_at is already set, the same settlement receipt is returned.

Settlement requires no balance due:

paid_cents must be >= total_cents at settlement time.

On settlement, the following snapshot fields are written exactly once:

settled_at

settled_total_cents

settled_paid_cents

settled_change_cents

settled_balance_due_cents

After settlement:

No new payments may be created for the order.

No cash-out may be created for the order.

Order status changes are blocked (as enforced by serializer validation).

Receipt rendering must use snapshot totals:

total_cents should reflect settled_total_cents

paid_cents should reflect settled_paid_cents

balance/change should reflect snapshot intent

Idempotency Requirements

Idempotency prevents duplicate money events on retries.

Payments:

pickup-payment and cash-out endpoints must support idempotency via reference.

If a payment with the same reference already exists for the tenant, return it instead of creating another.

For CASH overpay change, the OUT change record must also be idempotent and derived from reference (example: reference-change).

Settlement:

Calling settle twice returns the existing settled receipt.

What Is Allowed vs Not Allowed

Allowed:

Create new Payment rows to record new money events.

Create OUT payments to record refunds or change-outs.

Create Adjustment rows (APPLIED or VOIDED) for non-payment accounting changes.

Recompute totals via recalc_order_totals as needed.

Not allowed:

Mutating or “correcting” existing Payment/Adjustment history.

Changing the logic of settled snapshot usage without updating tests.

Adding new money math anywhere outside recalc_order_totals and receipt computation rules above.

Making PDF output differ from receipt presenter data.

Testing Expectations

Tests must continue to enforce:

settlement stability (reprint-safe receipts)

tenant isolation

idempotency for payment and settlement

receipt presenter as the single source of truth for JSON and PDF

Any change to financial logic must be accompanied by:

an updated test that proves the new rule

an explanation in the PR/commit message why the invariant changed
