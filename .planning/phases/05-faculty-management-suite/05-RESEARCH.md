# Phase 5 Research: Faculty Management Suite

## Executive Summary

Phase 5 introduces tenant-scoped **Faculty Management** for School Administrators. It establishes the `Faculty` model, race-condition-safe employee code auto-generation service, 3-layer defense-in-depth CRUD views (List, Create, Edit, Toggle Status), and an Apple Design System table interface with real-time client-side search, department filtering, and status badges.

---

## 1. Architecture & Data Model Patterns

### 1.1 `Faculty` Model Structure
The `Faculty` model inherits from `TenantModel` (defined in `apps/tenants/models.py`), automatically securing all queries with `TenantManager` and binding a `school` ForeignKey.

```python
from django.db import models
from apps.tenants.models import TenantModel
from apps.accounts.models import User

class Faculty(TenantModel):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,  # SET_NULL preserves historical attendance data if User is deleted
        related_name='faculty_profile',
        null=True,
        blank=True
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)  # Globally unique to align with User.email
    phone_number = models.CharField(max_length=20, blank=True)
    employee_code = models.CharField(max_length=50, db_index=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    date_joined = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_face_enrolled = models.BooleanField(default=False, help_text="Architecture hook for Phase 6 vector status")

    class Meta:
        ordering = ['first_name', 'last_name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'employee_code'],
                name='unique_faculty_code_per_school'
            ),
        ]
```

### 1.2 Race-Condition-Safe Employee Code Auto-Generation Algorithm
To prevent race conditions during concurrent faculty creation requests:
- Pattern: `{SUBDOMAIN_UPPER}-FAC-{COUNTER:03d}` (e.g., `GREENWOOD-FAC-001`).
- Atomic candidate generation with DB collision retry loop (`IntegrityError` catch) inside `@transaction.atomic`.

```python
@staticmethod
def generate_employee_code(school):
    prefix = f"{school.subdomain.upper()}-FAC-"
    # Start sequence from highest existing numeric suffix + 1
    existing_codes = Faculty.objects.filter(school=school, employee_code__startswith=prefix)\
                                    .values_list('employee_code', flat=True)
    numbers = []
    for code in existing_codes:
        suffix = code.replace(prefix, '')
        if suffix.isdigit():
            numbers.append(int(suffix))
    next_num = max(numbers, default=0) + 1
    return f"{prefix}{next_num:03d}"
```

### 1.3 Faculty User Account Security Boundary ( AUTH-02 / Privacy Directive )
- When a `Faculty` record is saved, a linked `User` record is automatically created/updated with `role=FACULTY` and `school=active_tenant`.
- Password: `user.set_unusable_password()`.
- Access Control: `TenantAwareAuthBackend` and `TenantLoginView` reject `FACULTY` role from web login. Faculty members do NOT log into the admin dashboard; their identity is used solely for attendance face matching.

### 1.4 3-Layer Defense-In-Depth Security Architecture
Security for all Faculty CRUD operations is enforced across 3 distinct layers:
1. **Layer 1 (Middleware)**: `TenantRoleAccessMiddleware` rejects unauthorized role/path combinations.
2. **Layer 2 (View Mixins)**: `SchoolAdminRequiredMixin` verifies `request.user.role == SCHOOL_ADMIN` and `request.user.school == request.tenant`.
3. **Layer 3 (Explicit Query & DB Isolation)**: Views explicitly query `Faculty.objects.filter(school=request.tenant, pk=pk)`. DB-level `UniqueConstraint(fields=['school', 'employee_code'])` enforces tenant uniqueness.

---

## 2. Standard Stack & UI Patterns

### 2.1 Apple Design System Table & Filter UI
- **Canvas & Card**: `#f5f5f7` canvas, `#ffffff` card container with `border border-gray-200/80` and `rounded-2xl`.
- **Search & Filters**:
  - Search input with eye-friendly `#fafafc` background and `#0066cc` focus ring.
  - Department Dropdown filter dynamically populated from active tenant's faculty departments.
  - Status Filter pills (`All`, `Active`, `Inactive`).
- **Badges**:
  - `Active`: Soft green (`bg-emerald-50 text-emerald-700 border-emerald-100`).
  - `Inactive`: Soft gray (`bg-gray-100 text-gray-600 border-gray-200`).
  - `Face Status`: `Pending` amber pill (`bg-amber-50 text-amber-700 border-amber-100`) ready for Phase 6.

---

## 3. Don't Hand-Roll

- **Do NOT hand-roll tenant filtering**: Use `TenantModel` and `TenantManager` (`Faculty.objects.for_tenant(request.tenant)`) + explicit `school=request.tenant` query filters — never issue raw `Faculty.objects.all()` queries.
- **Do NOT hand-roll modal JS framework**: Use simple, robust vanilla JS modal toggle handlers with backdrop blur and Esc key dismiss listeners.
- **Do NOT create fake face enrollment logic**: Keep `is_face_enrolled` as a clean boolean field on the model; Phase 6 will attach the webcam vector engine.

---

## 4. Common Pitfalls & Edge Cases

1. **Email Conflict between User and Faculty**:
   - `Faculty.email` is globally unique (`unique=True`), matching `User.email` constraint to prevent account creation conflicts.

2. **Faculty Deactivation vs Deletion**:
   - Never hard delete faculty records. Toggling status to `is_active=False` preserves historical records for attendance reporting while disabling active check-ins.

3. **Cascading Linked User Status**:
   - Toggling `is_active` on `Faculty` also updates `user.is_active` on the linked `User` record.
   - Deleting a `User` sets `faculty.user` to `NULL` via `SET_NULL`, keeping the `Faculty` profile and attendance logs intact.

---

## 5. Verification Plan

- **Automated Tests (`tests_faculty.py`)**:
  - Verify tenant isolation (School A admin attempting ID manipulation on School B faculty receives HTTP 404/403).
  - Verify Employee Code auto-generation logic (`GREENWOOD-FAC-001`) and race-condition safety.
  - Verify linked `User` creation with `set_unusable_password()` and `FACULTY` role.
  - Verify `on_delete=SET_NULL` integrity (deleting User retains Faculty record).
  - Verify `SchoolAdminRequiredMixin` protects all faculty endpoints.
