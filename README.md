# Dry Cleaners SaaS (Location-Based POS, Inventory, Billing)

A **multi-tenant (one tenant = one store location)** dry cleaner management platform built with  
**Django REST Framework**, **PostgreSQL**, and **React (Vite)** using **Tailwind + shadcn/ui**.

Designed as a production-grade SaaS backend with **strict tenant isolation**,  
**auditable financial flows**, and **operator-first workflows**.

---

## Local URLs

- **Database (Docker)**: `127.0.0.1:5433`
- **Backend API**: http://127.0.0.1:8000
- **API Docs (Swagger)**: http://127.0.0.1:8000/api/docs/
- **Frontend**: http://localhost:5173

---

## Why This Exists

Most dry cleaners still rely on paper tickets, spreadsheets, or outdated POS systems.

This project focuses on:

- Fast counter workflow (drop-off → processing → pickup)
- Item-level tracking (each garment = one OrderItem)
- Accurate billing with immutable audit trails
- Store-level tenant isolation for SaaS scalability

---

## ✨ Features

### SaaS & Security
- ✅ Tenant isolation (one store = one tenant)
- ✅ Tenant resolved via middleware (`X-Tenant`)
- 🔜 RBAC (Owner / Manager / Staff)

---

### Customer Management
- ✅ Customer profiles
- ✅ Phone normalization + fast lookup
- ✅ Full order history per customer
- ✅ Attach customer to order by ID or phone

---

### Orders & Lifecycle
- ✅ Orders + OrderItems (each item = one garment)
- ✅ Validated status transitions
- ✅ Immutable status audit log
- ✅ Lifecycle timestamps:
  - received_at
  - in_progress_at
  - ready_at
  - picked_up_at
  - cancelled_at

---

### Operator Workflows
- ✅ Order queues by status  
  (`/api/orders/queue/?status=READY`)
- ✅ Ready-but-unpaid queue
- ✅ Order timeline view (operator audit visibility)
- ✅ Receipt summary endpoint  
  (`/api/orders/{id}/receipt/summary/`)
- 🔜 Pickup preview endpoint

---

### Pickup Workflow
- ✅ READY → PICKED_UP flow
- ✅ Prevent invalid post-pickup transitions
- ✅ Explicit pickup endpoint
- ✅ Settlement-safe pickup logic

---

### Billing & Accounting
- ✅ Itemized receipts
- ✅ Payments (create / void / refund)
- ✅ Post-settlement adjustments
- ✅ Settlement snapshots:
  - total
  - paid
  - change
  - balance due
- ✅ Idempotent settlement logic
- ✅ Transaction-safe money math

---

### Tags & Printing (Planned)
- 🔜 Per-garment tag printing
- 🔜 Invoice number printed on each tag
- 🔜 Optional barcode / QR support
- 🔜 Reprint-safe tag workflow

*(Printing hardware integration intentionally deferred.)*

---

## 🧱 Tech Stack

### Backend
- Django 4.x
- Django REST Framework
- PostgreSQL
- SimpleJWT
- drf-spectacular (OpenAPI)

### Frontend
- React (Vite)
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query

### Dev & Ops
- Docker Compose (local Postgres)
- GitHub Actions CI
- Tenant-safe middleware architecture

---

## 🗺️ Architecture (High Level)

- **Tenant = physical store**
- Tenant context resolved server-side
- Client never sends `tenant_id`
- Financial operations are transactional + auditable
- Status changes are immutable events

See: `docs/ARCHITECTURE.md`

---

## ✅ Milestones

- ✅ **M0**: Repo + CI scaffold
- ✅ **M1**: Backend + frontend scaffold
- ✅ **M2**: Tenant isolation + middleware
- ✅ **M3**: Customers + lookup + history
- ✅ **M4**: Orders + items + receipts
- ✅ **M5**: Payments + settlement + pickup
- ✅ **M6**: Operator workflows (queues, timelines, dashboards)
- 🔜 **M7**: RBAC
- 🔜 **M8**: Deploy staging + prod

---

## 🧪 Testing

Operator safety suite:

`pytest -m operator_safety` (run from `backend/`)

This suite locks operator‑critical response shapes and financial invariants.

---

## 📄 License

No license selected yet (SaaS-oriented).
