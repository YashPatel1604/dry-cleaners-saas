# Dry Cleaners SaaS (Location-Based POS, Inventory, Billing)

A **multi-tenant (one tenant = one store location)** dry cleaner management platform built with **Django REST Framework**, **PostgreSQL**, and **React (Vite)** using **Tailwind + shadcn/ui**.  
Designed as a subscription SaaS product with strong data isolation, role-based access, and scalable deployment patterns.

## localhosts

DB (Docker): 127.0.0.1:5433
Backend: http://127.0.0.1:8000
API Docs: http://127.0.0.1:8000/api/docs/
Frontend: http://localhost:5173

## Why this exists

Dry cleaners often rely on paper tickets, spreadsheets, or outdated POS systems. This project focuses on:

- fast counter workflow (drop-off / pickup)
- item-level tracking and status updates
- accurate billing + payment audit trail
- store-level tenant isolation to support SaaS subscriptions

## ✨ Features (Planned / In Progress)

### SaaS & Security

- [ ] Tenant isolation (one store = one tenant)
- [ ] Membership + roles (Owner / Manager / Cashier / Staff)
- [ ] Audit log for sensitive actions (payments, refunds, overrides)

### Core Operations

- [ ] Customer profiles + phone search
- [ ] Drop-off order creation (items, notes, promised date)
- [ ] Tag codes for each item (barcode/QR-friendly)
- [ ] Item lifecycle: Received → Cleaning → QC → Ready → Picked up
- [ ] Pickup workflow with partial pickup support

### Billing & Reporting

- [ ] Payments: deposit / final / refund (transactional)
- [ ] Daily totals + payment method breakdown
- [ ] Open orders aging report

### Printing

- [ ] Printable receipts + item labels (browser print MVP)

### Subscription Rails (later)

- [ ] Tenant plan + billing_status fields (Stripe integration later)

## 🧱 Tech Stack

**Backend**

- Django + Django REST Framework
- PostgreSQL
- JWT auth (SimpleJWT)
- OpenAPI/Swagger (drf-spectacular)

**Frontend**

- React (Vite) + TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query

**Dev**

- Docker Compose (local Postgres)
- GitHub Actions CI (lint/test/build)

## 🗺️ Architecture (High Level)

- **Tenant = one physical store location**
- Tenant context is resolved via header in dev and subdomain in production
- Tenant-owned data is always scoped server-side (no `tenant_id` accepted from client)
- Payments and pickup operations are transactional and auditable

See: `docs/ARCHITECTURE.md`

## 🚀 Getting Started (Local Dev)

> Coming soon. This section will be filled in as the scaffold lands.

## ✅ Milestones

- [x] M0: GitHub repo setup (docs/templates/CI skeleton)
- [x] M1: Backend + frontend scaffold + local Postgres
- [ ] M2: Tenant + membership + tenant scoping middleware
- [ ] M3: Customers + search API + UI
- [ ] M4: Orders + items + tagging + printing
- [ ] M5: Pickup + payments + reports
- [ ] M6: Deploy staging + production

## 📸 Screenshots

> Add screenshots/GIFs here as features land.

## 📄 License

No license selected yet (SaaS-oriented). Can be added later.
