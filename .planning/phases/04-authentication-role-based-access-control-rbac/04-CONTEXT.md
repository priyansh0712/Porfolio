# Phase 04: Authentication & Role-Based Access Control (RBAC) - Context

**Gathered:** 2026-08-12  
**Status:** Ready for planning  
**Source:** User Discussion (`/gsd-discuss-phase 4`)

---

<domain>
## Phase Boundary

Build custom user model, Argon2id security, email authentication, role-based access control (`SUPER_ADMIN`, `SCHOOL_ADMIN`, `FACULTY`), subdomain login routing, post-login dashboards, and strict Super Admin privacy boundaries blocking access to tenant faculty & biometric records.
</domain>

<decisions>
## Implementation Decisions

### 1. Custom User Model & Role Architecture
- **Model**: `User` extending Django `AbstractUser` in `apps.accounts.models.py`.
- **Primary Credential**: Email address (`USERNAME_FIELD = 'email'`). Unique constraint on email.
- **Roles**:
  - `SUPER_ADMIN` = Platform owner / system administrator.
  - `SCHOOL_ADMIN` = Authorized school tenant administrator.
  - `FACULTY` = School faculty member (webcam attendance user).
- **School Association Rules**:
  - `SUPER_ADMIN`: `school` MUST be `None` (database `NULL`).
  - `SCHOOL_ADMIN`: `school` is **required** (database `NOT NULL`).
  - `FACULTY`: `school` is **required** (database `NOT NULL`).
- **Validation**: Enforced via Model `clean()` method and Django `CheckConstraint` at the DB level.

### 2. Login Routing & Post-Login Redirection
- **Tenant Login**: School Admins and Faculty log in at `schoola.localhost:8000/login/`.
- **Super Admin Login**: Super Admin logs in at root domain `localhost:8000/superadmin/login/`.
- **Subdomain Mismatch**: Logging in with a user belonging to School A on `schoolb.localhost:8000` is rejected with an explicit error alert.
- **Post-Login Redirects**:
  - `SCHOOL_ADMIN` / `FACULTY` → `/dashboard/` on tenant subdomain.
  - `SUPER_ADMIN` → `/superadmin/` on root domain.

### 3. Super Admin Privacy Boundaries (AUTH-02)
- **Privacy Rule**: Super Admin manages school tenant lifecycles but is strictly BLOCKED from accessing individual faculty profiles, biometrics, or attendance logs.
- **Enforcement**: Central RBAC Middleware (`TenantRoleAccessMiddleware`) + Decorators (`@school_admin_required`, `@super_admin_required`).
- **Forbidden Routes**: Any request by a `SUPER_ADMIN` to `/faculty/*`, `/biometrics/*`, `/attendance/*`, or `/reports/*` returns `HTTP 403 Forbidden` or redirects to `/superadmin/` with a privacy warning.

### 4. Session Security & Cookie Isolation
- **Session Duration**: 8-hour fixed session timeout (`SESSION_COOKIE_AGE = 28800`).
- **Cookie Isolation**: `SESSION_COOKIE_DOMAIN = None` — session cookies are bound strictly to the specific subdomain host (`schoola.localhost` session cannot be reused on `schoolb.localhost`).
- **Password Hashing**: Uses `Argon2id` (configured in Phase 1).

</decisions>

<canonical_refs>
## Canonical References

- `.planning/PROJECT.md` — Multi-tenant SaaS privacy & security rules.
- `.planning/ROADMAP.md` — Phase 4 scope (AUTH-01, AUTH-02, AUTH-03).
- `apps/tenants/middleware.py` — `TenantMiddleware` and `request.tenant` binding.
- `apps/tenants/models.py` — `School` and `TenantModel` base classes.
</canonical_refs>

<deferred>
## Deferred Ideas

- Social Auth (OAuth2 / Google Workspace SSO) — out of scope for initial MVP.
- Multi-factor authentication (TOTP/2FA) for School Admins — deferred to post-MVP security milestone.
</deferred>
