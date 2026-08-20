# Phase 3: Multi-Tenant Subdomain Infrastructure - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 implements multi-tenant subdomain resolution and data isolation infrastructure. It delivers `TenantMiddleware` for parsing request hosts (`school.ourapp.com` / `school.localhost:8000`), resolving `School` tenant instances, enforcing strict domain/subdomain routing separation, handling invalid subdomain fallbacks gracefully, and establishing `TenantModel` base class with auto-scoping managers to prevent cross-tenant data leakage.

</domain>

<decisions>
## Implementation Decisions

### Subdomain Resolution & Fallback Behavior
- **D-01:** Subdomain detection parses `request.get_host()`.
  - Root domain (`localhost:8000`, `ourapp.com`) -> `request.tenant = None` (Public Context).
  - Subdomain (`schoola.localhost:8000`, `schoola.ourapp.com`) -> Resolves `School` tenant from database.
- **D-02:** If an unassigned or non-existent subdomain is accessed, `TenantMiddleware` redirects to the main landing page (`/`) on the root domain with a Django flash alert message (`messages.error(request, "School tenant not found.")`).

### Local Development Configuration
- **D-03:** Use browser-native `.localhost` subdomain routing (`schoola.localhost:8000`) for local development without requiring system `hosts` file modifications.
- **D-04:** `ALLOWED_HOSTS` includes `127.0.0.1`, `localhost`, `.localhost`, `.ourapp.com`.

### Multi-Tenant Data Isolation Strategy
- **D-05:** Implement `TenantModel` abstract base class in `apps/tenants/models.py` inheriting from `TimeStampedModel`. `TenantModel` includes a mandatory `school` ForeignKey to `School`.
- **D-06:** Implement `TenantManager` / `TenantQuerySet` base manager that automatically scopes database queries to the active tenant in `request.tenant` to prevent cross-tenant query leaks.

### Public vs Tenant Route Separation
- **D-07:** Enforce Strict Subdomain Routing:
  - Root domain strictly serves Public pages (Landing Page, School Self-Registration, Success View).
  - Subdomains strictly serve Tenant-scoped views and dashboards. If a public page is accessed on a subdomain, or a tenant view is accessed on root domain, the middleware enforces proper routing boundaries.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/PROJECT.md` — Core value, tenant isolation constraints, multi-tenancy principles
- `.planning/REQUIREMENTS.md` — `TENANT-01` multi-tenant isolation requirement
- `.planning/research/ARCHITECTURE.md` — Multi-tenant architecture and middleware data flow
- `apps/tenants/models.py` — Existing `School` tenant model (`name`, `subdomain`, `created_at`)
- `apps/public/views.py` — Public views to be served on root domain

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/tenants/models.py`: `School` model with `subdomain` field and unique constraint.
- `apps/core/models.py`: `TimeStampedModel` abstract base class.
- `templates/components/alerts.html`: Flash alert message rendering.

### Established Patterns
- Django custom middleware pattern in `apps/tenants/middleware.py`.
- Split settings in `config/settings/base.py` for middleware loading order.

</code_context>

<specifics>
## Specific Ideas

- Ensure `TenantMiddleware` is placed early in `MIDDLEWARE` setting (after `SessionMiddleware` and `AuthenticationMiddleware` if auth context is needed, or immediately before view resolution).
- Add test suite in `apps/tenants/tests_middleware.py` verifying subdomain resolution, invalid subdomain redirection, and tenant query scoping.

</specifics>

<deferred>
## Deferred Ideas

None — discussion focused strictly on Phase 3 subdomain & multi-tenant isolation scope.

</deferred>

---

*Phase: 03-multi-tenant-subdomain-infrastructure*
*Context gathered: 2026-08-11*
