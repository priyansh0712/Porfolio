# Phase 4: Authentication & Role-Based Access Control (RBAC) - Research

**Phase:** 04 - Authentication & Role-Based Access Control (RBAC)  
**Date:** 2026-08-12  
**Status:** Complete  

---

## Standard Stack

| Layer | Recommended Technology | Rationale |
|-------|-----------------------|-----------|
| **User Model** | Custom `User` extending `AbstractUser` | Allows email as `USERNAME_FIELD`, `role` enum, and `school` FK with DB-level check constraints. |
| **Password Hashing** | `Argon2id` (`Argon2PasswordHasher`) | Memory-hard security algorithm configured in `config/settings/base.py`. |
| **Authentication Backend** | `TenantAwareAuthBackend` | Authenticates email + password and verifies user's `school` matches `request.tenant` (or is Super Admin on root domain). |
| **Defense-in-Depth Security** | 3-Layer Security (Middleware + View Mixin + Query Scoping) | Zero single point of failure; security remains intact even if a developer omits a decorator or middleware fails. |
| **Session Isolation** | Subdomain-Bound Cookies (`SESSION_COOKIE_DOMAIN = None`) | Prevents session hijacking or cross-subdomain session reuse between schools. |

---

## Architecture Patterns

### 1. Custom User Model & DB Constraints
```python
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Platform Super Admin'
        SCHOOL_ADMIN = 'SCHOOL_ADMIN', 'School Administrator'
        FACULTY = 'FACULTY', 'School Faculty'

    email = models.EmailField('Email Address', unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.FACULTY)
    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        help_text='School tenant association. Null for Super Admin.'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        constraints = [
            # Super Admin MUST NOT have a school tenant assigned
            models.CheckConstraint(
                check=models.Q(role='SUPER_ADMIN', school__isnull=True) | ~models.Q(role='SUPER_ADMIN'),
                name='super_admin_no_school'
            ),
            # School Admin and Faculty MUST have a school tenant assigned
            models.CheckConstraint(
                check=models.Q(role__in=['SCHOOL_ADMIN', 'FACULTY'], school__isnull=False) | models.Q(role='SUPER_ADMIN'),
                name='tenant_user_requires_school'
            ),
        ]

    def clean(self):
        super().clean()
        if self.role == self.Role.SUPER_ADMIN and self.school_id is not None:
            raise ValidationError({'school': 'Platform Super Admin must not be assigned to a school tenant.'})
        if self.role in (self.Role.SCHOOL_ADMIN, self.Role.FACULTY) and self.school_id is None:
            raise ValidationError({'school': 'School Admin and Faculty must be assigned to a school tenant.'})
```

### 2. 3-Layer Defense-in-Depth Security Strategy

```
┌────────────────────────────────────────────────────────┐
│ Layer 1: TenantRoleAccessMiddleware                   │
│ Checks Host Header vs User Role on every request       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Layer 2: View Permission Mixin / Decorator             │
│ @school_admin_required / SchoolAdminRequiredMixin     │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Layer 3: Query & Service Layer Explicit Scoping        │
│ .filter(school=request.tenant) + object permission check│
└────────────────────────────────────────────────────────┘
```

#### Layer 1: Middleware Guard (`TenantRoleAccessMiddleware`)
- Rejects Super Admin requests to tenant-scoped endpoints (`/faculty/*`, `/biometrics/*`, `/attendance/*`, `/reports/*`) with HTTP 403 Forbidden.
- Rejects School Admin / Faculty requests on root domain (`localhost:8000/superadmin/*`).

#### Layer 2: View Permission Decorators & Mixins
- `SchoolAdminRequiredMixin` & `@school_admin_required`: Ensures `request.user.is_authenticated` and `request.user.role == Role.SCHOOL_ADMIN` and `request.user.school == request.tenant`.
- `SuperAdminRequiredMixin` & `@super_admin_required`: Ensures `request.user.is_authenticated` and `request.user.role == Role.SUPER_ADMIN` and `request.tenant is None`.

#### Layer 3: Query / Service Explicit Scoping
- Views explicitly filter querysets with `.filter(school=request.tenant)` and validate `instance.school == request.tenant` on updates/deletions. Never relies solely on `TenantManager` magic.

---

## Don't Hand-Roll

- **Don't hand-roll password hashing**: Use Django's built-in `make_password` / `check_password` with `Argon2id`.
- **Don't hand-roll session cookie management**: Use Django session framework with `SESSION_COOKIE_AGE = 28800` (8 hours).
- **Don't hardcode permission checks in template logic alone**: Template hiding is cosmetic; authorization MUST be enforced in backend views and middleware.

---

## Common Pitfalls

1. **AUTH_USER_MODEL Missing in Settings**: `AUTH_USER_MODEL = 'accounts.User'` MUST be added to `config/settings/base.py` before running `makemigrations`.
2. **Subdomain Cross-Tenant Login Flaw**: A user registered at School A might try logging in at `schoolb.localhost:8000/login/`. `TenantAwareAuthBackend` MUST check `user.school == request.tenant` during authentication.
3. **Super Admin Privacy Leak**: Super Admin should NOT have access to faculty list or biometric embeddings. Layer 1 Middleware + Layer 2 Mixins MUST return 403 Forbidden for Super Admin on all tenant-scoped routes.

---

## Downstream Guidance for `/gsd-plan-phase 4`

- **Plan 04-01**: Custom `User` model (`apps/accounts/models.py`), Argon2id settings (`AUTH_USER_MODEL`), Tenant-aware auth backend, forms, login/logout views, and `SchoolAdminRequiredMixin`.
- **Plan 04-02**: `TenantRoleAccessMiddleware` (Layer 1 guard), Super Admin platform dashboard view on root domain, privacy boundary enforcement, and comprehensive automated RBAC test suite (`apps/accounts/tests_rbac.py`).
