# Phase 5 Research: Faculty Management Suite

## Executive Summary

Phase 5 introduces tenant-scoped **Faculty Management** for School Administrators. It establishes the `Faculty` model, tenant-scoped sequence counter with `select_for_update()` DB row locking for employee code auto-generation, 3-layer defense-in-depth CRUD views (List, Create, Edit, Toggle Status), and an Apple Design System table interface with real-time client-side search, department filtering, and status badges.

---

## 1. Architecture & Data Model Patterns

### 1.1 `Faculty` & `TenantSequence` Model Structure
The `Faculty` model inherits from `TenantModel` (defined in `apps/tenants/models.py`), automatically securing all queries with `TenantManager` and binding a `school` ForeignKey.

```python
from django.db import models
from apps.tenants.models import TenantModel
from apps.accounts.models import User

class TenantSequence(TenantModel):
    """
    Tenant-scoped sequence counter for concurrency-safe sequential code generation.
    Uses select_for_update() row-level locking to prevent race conditions.
    """
    sequence_type = models.CharField(max_length=50, default='FACULTY')
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'sequence_type'],
                name='unique_tenant_sequence_type'
            )
        ]


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

### 1.2 Tenant-Scoped Sequence Generator with DB Row Locking (`select_for_update`)
To guarantee 100% concurrency safety and zero sequence gaps during high-traffic faculty creation:
- Pattern: `{SUBDOMAIN_UPPER}-FAC-{SEQUENCE_VALUE:03d}` (e.g., `GREENWOOD-FAC-001`).
- Algorithm obtains a DB row lock on `TenantSequence` using `select_for_update()` inside `@transaction.atomic`.

```python
from django.db import transaction

class FacultyCodeService:
    @staticmethod
    @transaction.atomic
    def generate_next_code(school) -> str:
        """
        Generates the next sequential employee code for the given tenant school.
        Uses select_for_update() row lock to eliminate race conditions under load.
        """
        seq, created = TenantSequence.objects.select_for_update().get_or_create(
            school=school,
            sequence_type='FACULTY',
            defaults={'last_value': 0}
        )
        seq.last_value += 1
        seq.save(update_fields=['last_value', 'updated_at'])
        
        prefix = school.subdomain.upper()
        return f"{prefix}-FAC-{seq.last_value:03d}"
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
- **Do NOT hand-roll sequence locking**: Use `TenantSequence` with `select_for_update()` inside `@transaction.atomic`.
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
  - Verify `FacultyCodeService` sequence counter and `select_for_update()` locking under concurrent calls (`GREENWOOD-FAC-001`, `GREENWOOD-FAC-002`).
  - Verify linked `User` creation with `set_unusable_password()` and `FACULTY` role.
  - Verify `on_delete=SET_NULL` integrity (deleting User retains Faculty record).
  - Verify `SchoolAdminRequiredMixin` protects all faculty endpoints.
