# Plan 04-01 Summary: Custom User Model, Auth Backend & Login Views

**Phase:** 04-authentication-role-based-access-control-rbac
**Plan:** 01 — Custom User Model, TenantAwareAuthBackend, Login Views & Templates
**Status:** ✅ Complete
**Commits:** `f1db43e`, `44714a9`

## What Was Built

### 1. Custom User Model (`apps/accounts/models.py`)
- `User(AbstractUser)` with `USERNAME_FIELD = 'email'`.
- Role choices: `SUPER_ADMIN`, `SCHOOL_ADMIN`, `FACULTY`.
- `school = ForeignKey('tenants.School', null=True, blank=True)`.
- DB `CheckConstraints`:
  - `super_admin_no_school`: Super Admin must have `school = NULL`.
  - `tenant_user_requires_school`: School Admin and Faculty must have `school != NULL`.
- Application-level `clean()` validation complementing DB constraints.
- `is_super_admin`, `is_school_admin`, `is_faculty` convenience properties.

### 2. Custom UserAdmin (`apps/accounts/admin.py`)
- Registered with email, role, school, and is_active displayed in list view.

### 3. Settings Updates (`config/settings/base.py`)
- `AUTH_USER_MODEL = 'accounts.User'` registered.
- `AUTHENTICATION_BACKENDS = ['apps.accounts.auth_backends.TenantAwareAuthBackend', ...]`.
- `SESSION_COOKIE_AGE = 28800` (8-hour session).
- `SESSION_COOKIE_DOMAIN = None` (subdomain-isolated sessions).
- `LOGIN_URL = '/login/'`, `LOGIN_REDIRECT_URL = '/dashboard/'`.

### 4. TenantAwareAuthBackend (`apps/accounts/auth_backends.py`)
- Authenticates email + password with timing-attack protection.
- Enforces subdomain-role isolation:
  - Super Admin: login only on root domain (`request.tenant is None`).
  - School Admin / Faculty: login only on their school's subdomain (`user.school == request.tenant`).
  - Cross-tenant or role-mismatch returns `None` (silent rejection).

### 5. Login Form (`apps/accounts/forms.py`)
- `TenantLoginForm(AuthenticationForm)` with email input + Tailwind CSS styling.

### 6. Authentication Views (`apps/accounts/views.py`)
- `TenantLoginView`: email-based login with role-aware post-login redirect.
- `TenantLogoutView`: logs out and redirects to `/login/`.
- `TenantDashboardView(LoginRequiredMixin)`: School Admin welcome dashboard.

### 7. URL Patterns (`apps/accounts/urls.py`)
- `/login/`, `/logout/`, `/dashboard/` registered and included in `config/urls.py`.

### 8. Templates
- `templates/accounts/login.html`: Glassmorphism card with tenant branding, error alerts, and flash message rendering.
- `templates/accounts/dashboard.html`: School Admin dashboard with stat cards (School, Role, Status) and coming-soon action cards.

### 9. Database Migration
- `apps/accounts/migrations/0001_initial.py` created and applied cleanly.

## Verification
- `from apps.accounts.models import User` → ✅
- `from apps.accounts.auth_backends import TenantAwareAuthBackend` → ✅
- `python manage.py check` → ✅ System check identified no issues (0 silenced).
