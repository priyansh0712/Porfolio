# Phase 3: Multi-Tenant Subdomain Infrastructure - Discussion Log

**Date:** 2026-08-11

## Alternatives Considered & Rationale

### 1. Invalid Subdomain Handling
- **Alternative A**: Render standard 404 page.
- **Alternative B**: Dedicated 404 "School Not Found" page with CTA.
- **Selected**: Redirect to root domain (`/`) with Django alert message ("School tenant not found").
- **Rationale**: Provides smooth UX for lost users or mistyped subdomains without stranding them on a dead-end 404 page.

### 2. Local Subdomain Routing
- **Alternative A**: Custom local domain requiring system `hosts` file configuration (`school.ourapp.local`).
- **Selected**: Browser-native `.localhost` domain routing (`school.localhost:8000`).
- **Rationale**: Eliminates OS-level setup friction for developers and automated testing environments.

### 3. Multi-Tenant Data Isolation Strategy
- **Alternative A**: PostgreSQL schema-per-tenant isolation (`django-tenants`).
- **Selected**: Custom `TenantMiddleware` + `TenantModel` base class with auto-scoping `TenantManager`.
- **Rationale**: High performance, simple migrations, zero schema overhead, and complete row-level isolation ideal for multi-tenant SaaS architectures.

### 4. Public vs Tenant Route Separation
- **Alternative A**: Path-based fallback allow public URLs on subdomains.
- **Selected**: Strict Subdomain Routing (`localhost:8000` = Public, `school.localhost:8000` = Tenant).
- **Rationale**: Enforces clean security boundaries and prevents brand/content confusion between public marketing and private school tenant portals.
