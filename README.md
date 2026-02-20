# Dry Cleaners SaaS

Multi-tenant dry-cleaning POS and operations platform.

- Backend: Django 6 + DRF + PostgreSQL
- Frontend: React 19 + Vite + TypeScript + Tailwind + shadcn/ui
- Tenant model: one tenant = one physical store/location

---

## Local URLs

- Backend API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/api/docs/`
- Frontend: `http://localhost:5173`
- DB (local): `127.0.0.1:5433`

---

## What Is Implemented

### Multi-tenant + auth

- Tenant isolation via `X-Tenant` header and tenant membership checks.
- JWT auth (SimpleJWT).
- Tenant bootstrap/settings/member/invite flows.

### Customer workflows

- Customer create/search/update.
- Customer profile with order history.
- Drop-off flow starts from customer lookup or registration.

### Inventory workflows

- Inventory CRUD with SKU, active/archive state.
- Inventory image upload (file-based media).
- Inventory image removal from edit flow.

### Orders + lifecycle

- Order + OrderItem model with recalculated totals.
- Status flow with immutable status-event timeline.
- Key statuses: `RECEIVED`, `IN_PROGRESS`, `READY`, `COMPLETED`, `PICKED_UP`, `CANCELLED`.
- Order notes + timeline endpoints.

### Payments + settlement + receipts

- Captured IN/OUT payments, pickup-time payments, change handling.
- Idempotency on critical payment/pickup operations.
- Settlement snapshot fields for accounting stability.
- JSON receipt + PDF receipt endpoint parity.

### Order SKU + barcode + tags

- Auto-generated order SKU (`ORD-########`) per order.
- Barcode SVG endpoint per order.
- Order barcode shown in order detail.
- Tag print flow with barcode + SKU.
- Tenant settings for tag print size:
  - `2x1`
  - `4x2`
- Tenant fallback tag copies setting.
- New-order default print copies = total item quantity in that order.

### Dashboard/reporting

- Dashboard daily metrics include:
  - total invoices/orders today
  - total pieces received today
  - orders value today
  - collected amount today
- Reports endpoints for ops/workload/unpaid/summary/range.

### Storage location barcode flow (rack flow)

- Location assignment by scan flow:
  1. Scan location barcode.
  2. If location is new, optional rack number entry.
  3. Scan order barcode/SKU.
- Dedicated **Scan Station** mode for continuous scanning with always-focused inputs.
- Strict barcode rules enforced in API and UI:
  - location: `LOC-...`
  - order: `ORD-########`
- Current order detail shows location barcode + rack number.
- Pickup flow asks if location should be cleared.
- Rack occupancy guard:
  - A rack/location can only hold one active assigned order.
  - If occupied, API returns conflict and UI asks:
    - “Rack already full. Do you want to clear rack and continue?”
  - If confirmed, old assignment is cleared and new order is assigned.
- Rack status view shows each location as `Occupied`/`Empty` and current order SKU.
- Storage assignment history is logged with actor + timestamp:
  - assign
  - clear
  - force-clear eviction
  - visible via order timeline and storage history endpoint.
- Rack/location is intentionally **not** printed on receipt.

---

## Run Locally

## 1) Backend

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Testing

Run backend tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

Run operator safety suite:

```bash
cd backend
source .venv/bin/activate
pytest -m operator_safety
```

---

## Scanner Guidance (Store Rollout)

For real store hardware, use barcode scanners in HID keyboard mode:

- scanner acts like keyboard input
- append `Enter` suffix from scanner configuration
- scan fields in UI auto-submit and move to next step
- if a scanner reads `LOC-*` or `ORD-*` while no text field is focused, app auto-opens Orders scan station

This gives immediate compatibility without custom driver integration.

Detailed setup and operator SOP: `docs/SCANNER_SETUP_SOP.md`

---

## Known Current Gaps

- Frontend production build currently fails on an existing type issue in:
  - `frontend/src/components/AIAssistantDialog.tsx`
- No silent/background printer daemon integration yet (browser print flow used).
- No native scanner driver integration yet (HID keyboard mode only).
- No conveyor/carousel API integration yet.

---

## Future Work (Discussed, Not Done Yet)

### Scanner + operations hardening

- Bulk rack actions (clear/move many orders in one operation).
- Optional multi-capacity rack model (today capacity is 1 order per location barcode).
- Role-based controls around force-clear behavior.
- Mobile camera scanner fallback workflow.

### Hardware/automation integration

- Print service integration for direct thermal label printers.
- Conveyor/carousel system integration hooks.
- Optional RFID support later (currently barcode-only by decision).

### Product roadmap

- Role hardening/RBAC expansion.
- Deployment hardening and staging/production release workflows.
- Additional reporting and operational alerts.

---

## Repo Pointers

- API contract: `backend/API_CONTRACT.md`
- Architecture notes: `docs/ARCHITECTURE.md`
- Financial invariants: `docs/FINANCIAL_INVARIANTS.md`

---

## License

No license selected yet.
