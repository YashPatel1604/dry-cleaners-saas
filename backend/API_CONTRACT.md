# API Contract (Backend)

## Auth header
All authenticated endpoints require:

```
Authorization: Bearer <token>
```

## Tenant header rules
Tenant‑scoped endpoints require:

```
X-Tenant: <tenant_slug>
```

If the user is not a member of the tenant, the API returns `404` (anti‑enumeration).

## Global (non‑tenant) endpoints
These do **not** require `X-Tenant`:
- `GET /api/me/tenants/`
- `POST /api/invites/accept/`
- `POST /api/auth/password-reset/request/`
- `POST /api/auth/password-reset/confirm/`
- `POST /api/tenant/bootstrap/` (no tenant header required)

## Pagination conventions
Pagination is **optional** and uses `?limit=&offset=`. If provided, the response shape is unchanged and the server slices results.

Shapes used in this codebase:
- **Plain list** (no wrapper):
  - Customers list/search, Orders list/search, Invites list, Audit list, Notes list.
- **Count + results**:
  - Order cards: `{"count": int, "results": [...]}`
  - Unpaid report: `{"count": int, "results": [...]}`
- **Series**:
  - Reports range: `{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "series": [...]}`

## Canonical endpoints list

### Identity / tenant discovery
- `GET /api/me/tenants/`

### Orders (tenant‑scoped)
- `GET /api/orders/` (optional `limit/offset`)
- `GET /api/orders/search/?q=...&limit=&offset=`
- `GET /api/orders/cards/?q=...&status=...&limit=&offset=`
- `GET /api/orders/{id}/receipt/` (includes `pdf_url`)
- `GET /api/orders/{id}/receipt/print/` (PDF)
- `POST /api/orders/{id}/receipt/email/` (if enabled)
- `GET /api/orders/{id}/ticket.pdf/` (alias of receipt PDF)
- `POST /api/orders/{id}/mark_ready/`
- `GET /api/orders/{id}/notes/` (optional `limit/offset`)
- `POST /api/orders/{id}/notes/`
- `GET /api/orders/{id}/timeline/`

### Customers (tenant‑scoped)
- `GET /api/tenant/customers/` (optional `limit/offset`)
- `POST /api/tenant/customers/`
- `GET /api/tenant/customers/{id}/`
- `PATCH /api/tenant/customers/{id}/`
- `DELETE /api/tenant/customers/{id}/`
- `GET /api/tenant/customers/search/?q=...&limit=&offset=`
- `GET /api/tenant/customers/{id}/orders/`
- `POST /api/tenant/customers/{id}/orders/` (quick create)

### Invites (tenant‑scoped, OWNER_ADMIN)
- `GET /api/tenant/invites/` (optional `limit/offset`)
- `POST /api/tenant/invites/`
- `POST /api/tenant/invites/{id}/revoke/`

### Audit (tenant‑scoped, OWNER_ADMIN)
- `GET /api/tenant/audit/memberships/` (optional `limit/offset` + `before_id`)
- `GET /api/tenant/audit/config/` (optional `limit/offset` + `before_id`)
- `GET /api/tenant/audit/invites/` (optional `limit/offset` + `before_id`)

### Reports (tenant‑scoped, OWNER_ADMIN)
- `GET /api/tenant/reports/summary/?date=YYYY-MM-DD`
- `GET /api/tenant/reports/range/?start=YYYY-MM-DD&end=YYYY-MM-DD` (series; optional `limit/offset`)
- `GET /api/tenant/reports/unpaid/?limit=&offset=`

---

## Example curl commands

Set these once in your shell:
```bash
export BASE_URL="http://localhost:8000"
export TOKEN="YOUR_JWT"
export TENANT_SLUG="your-tenant-slug"
```

Tenant discovery:
```bash
curl -i "$BASE_URL/api/me/tenants/" \
  -H "Authorization: Bearer $TOKEN"
```

Order cards:
```bash
curl -i "$BASE_URL/api/orders/cards/?limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Order receipt (+ pdf_url):
```bash
curl -i "$BASE_URL/api/orders/123/receipt/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Receipt PDF:
```bash
curl -i "$BASE_URL/api/orders/123/receipt/print/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Ticket PDF:
```bash
curl -i "$BASE_URL/api/orders/123/ticket.pdf/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Mark ready:
```bash
curl -i -X POST "$BASE_URL/api/orders/123/mark_ready/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Order notes (create + list):
```bash
curl -i -X POST "$BASE_URL/api/orders/123/notes/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG" \
  -H "Content-Type: application/json" \
  -d '{"note":"Handle with care"}'

curl -i "$BASE_URL/api/orders/123/notes/?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Customer search:
```bash
curl -i "$BASE_URL/api/tenant/customers/search/?q=patel&limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Quick create order for customer:
```bash
curl -i -X POST "$BASE_URL/api/tenant/customers/456/orders/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Reports:
```bash
curl -i "$BASE_URL/api/tenant/reports/summary/?date=2026-01-15" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"

curl -i "$BASE_URL/api/tenant/reports/range/?start=2026-01-01&end=2026-01-07" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"

curl -i "$BASE_URL/api/tenant/reports/unpaid/?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant: $TENANT_SLUG"
```

Invite accept:
```bash
curl -i -X POST "$BASE_URL/api/invites/accept/" \
  -H "Content-Type: application/json" \
  -d '{"token":"INVITE_TOKEN","password":"TempPass123!"}'
```

Password reset:
```bash
curl -i -X POST "$BASE_URL/api/auth/password-reset/request/" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'

curl -i -X POST "$BASE_URL/api/auth/password-reset/confirm/" \
  -H "Content-Type: application/json" \
  -d '{"token":"RESET_TOKEN","new_password":"NewPass123!"}'
```

---

## Response examples (JSON)

### /api/orders/cards/
```json
{
  "count": 2,
  "results": [
    {
      "order_id": 123,
      "pickup_id": "123",
      "status": "READY",
      "created_at": "2026-01-22T16:23:13.900436-08:00",
      "updated_at": "2026-01-22T16:30:01.123456-08:00",
      "customer": {
        "id": 7,
        "name": "Patel",
        "phone": "7140000012",
        "email": "patel@example.com"
      },
      "money": {
        "total_cents": 1200,
        "net_paid_cents": 500,
        "balance_due_cents": 700,
        "change_due_cents": 0
      }
    }
  ]
}
```

### /api/orders/{id}/receipt/
```json
{
  "id": 123,
  "status": "READY",
  "due_at": "2026-01-23T17:00:00-08:00",
  "notes": "",
  "created_at": "2026-01-22T16:23:13.900436-08:00",
  "settled_at": null,
  "customer": { "id": 7, "name": "Patel", "phone": "7140000012", "email": "patel@example.com" },
  "items": [],
  "subtotal_cents": 1000,
  "tax_cents": 100,
  "total_cents": 1100,
  "paid_cents": 500,
  "adjustments_net_cents": 0,
  "net_paid_cents": 500,
  "balance_due_cents": 600,
  "change_due_cents": 0,
  "payments": [],
  "adjustments": [],
  "pdf_url": "http://localhost:8000/api/orders/123/receipt/print/"
}
```

### /api/orders/{id}/notes/
```json
[
  {
    "id": 1,
    "note": "Handle with care",
    "created_at": "2026-01-22T16:25:28.277206-08:00",
    "author_id": 2,
    "author_username": "operator1"
  }
]
```

### /api/orders/{id}/timeline/
```json
[
  {
    "id": "order:123",
    "at": "2026-01-22T16:23:13.900436-08:00",
    "created_at": "2026-01-22T16:23:13.900436-08:00",
    "kind": "order.created",
    "event_type": "order.created",
    "title": "Order created",
    "summary": "Order #123 created",
    "actor": { "type": "SYSTEM", "id": "", "label": "system" },
    "amount": null,
    "refs": { "order_id": 123, "status_event_id": null, "payment_id": null, "adjustment_id": null },
    "meta": {}
  }
]
```

### /api/tenant/reports/range/
```json
{
  "start": "2026-01-01",
  "end": "2026-01-07",
  "series": [
    {
      "date": "2026-01-01",
      "orders_created": 0,
      "orders_settled": 0,
      "net_sales_cents": 0,
      "net_paid_cents": 0,
      "balance_due_cents": 0
    }
  ]
}
```
