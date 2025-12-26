# Architecture

## Tenancy model
- One tenant represents one physical store location.
- All tenant-owned data is scoped server-side.
- Development: tenant can be resolved via a request header.
- Production: tenant will be resolved via subdomain.

## High-level components
- Backend API: Django REST Framework + PostgreSQL
- Frontend: React (Vite) + Tailwind + shadcn/ui
