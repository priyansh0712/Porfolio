# Phase 04: Authentication & Role-Based Access Control (RBAC) - Discussion Log

**Date:** 2026-08-12  
**Participants:** USER, Antigravity AI  

---

## Gray Areas Explored & Decided

### 1. User Model & Roles
- **Q**: Should login use Username or Email?
- **Decision**: Email address (`USERNAME_FIELD = 'email'`).
- **Q**: How should Roles be defined and associated with Schools?
- **Decision**: Custom `User` model with `role` field (`SUPER_ADMIN`, `SCHOOL_ADMIN`, `FACULTY`) and `school` FK to `tenants.School`.
- **Constraint (User Note)**: `SUPER_ADMIN` must have `school = NULL`. `SCHOOL_ADMIN` and `FACULTY` must have required `school` FK. Enforced via `clean()` and DB `CheckConstraint`.

### 2. Subdomain Login & Redirection
- **Q**: Should login be on Subdomains or Root domain?
- **Decision**: Strict Subdomain Login (`schoola.localhost:8000/login/` for tenant admins; `localhost:8000/superadmin/login/` for Super Admin).
- **Q**: Post-login redirection target?
- **Decision**: School Admin -> `/dashboard/` on tenant subdomain; Super Admin -> `/superadmin/` on root domain.

### 3. Super Admin Privacy Boundaries
- **Q**: How to block Super Admin from tenant faculty/attendance data?
- **Decision**: Central RBAC Middleware + `@school_admin_required` decorators. Reject Super Admin access (HTTP 403 / Redirect) on all tenant-scoped routes.

### 4. Session Security & Isolation
- **Q**: Session timeout policy?
- **Decision**: 8-hour fixed session timeout (`SESSION_COOKIE_AGE = 28800`).
- **Q**: Session cookie domain?
- **Decision**: Subdomain-isolated session cookies (`SESSION_COOKIE_DOMAIN = None`).
