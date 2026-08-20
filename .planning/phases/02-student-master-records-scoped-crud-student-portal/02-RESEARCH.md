# Phase 2: Student Master Records, Scoped CRUD & Student Portal - Research

## Executive Summary
Phase 2 builds the core student information architecture and role-scoped permissions for StudentERP1. It establishes the `apps.students` Django application, introduces the `Student` and `StudentTransferRequest` data models with tenant isolation, expands user authentication with `Role.STUDENT` allowing GR-based login (`Admin@123`), enforces Class Teacher scoped CRUD boundaries (locked GR numbers), implements the Principal transfer approval workflow, and creates responsive Apple Design System UI interfaces for both School Staff and Students.

---

## 1. Standard Stack & Architecture Patterns

### Technologies & Dependencies
| Component | Implementation | Notes |
|---|---|---|
| **App Namespace** | `apps.students` | Registered in `config/settings/base.py` and `config/urls.py` |
| **Authentication** | `apps.accounts.backends.TenantAuthBackend` | Dual-mode login supporting Email (Staff) and GR Number (Students) on school subdomains |
| **User Role** | `apps.accounts.models.User.Role.STUDENT` | Extends check constraints to enforce tenant FK for students |
| **Service Layer** | `apps.students.services.StudentService` | Atomic business transactions (student registration, user provisioning, transfers) |
| **UI Templates** | `templates/students/` + Vanilla JS | Apple Design System (`SF Pro`, `#f5f5f7`, `#0066cc`, soft pill badges, modal dialogs) |

---

## 2. Data Models Architecture

### A. `Student` Model (`apps/students/models.py`)
```python
class Student(models.Model):
    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    class BloodGroup(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'

    school = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='students')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile')
    gr_number = models.CharField(max_length=50, db_index=True)
    roll_number = models.PositiveIntegerField(null=True, blank=True)
    full_name = models.CharField(max_length=255)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    blood_group = models.CharField(max_length=5, choices=BloodGroup.choices, blank=True, default='')
    
    # Guardian details
    guardian_name = models.CharField(max_length=255, blank=True, default='')
    guardian_phone = models.CharField(max_length=20, blank=True, default='')
    emergency_contact = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')

    # Academic Placement
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE, related_name='students')
    standard = models.ForeignKey('academics.Standard', on_delete=models.CASCADE, related_name='students')
    division = models.ForeignKey('academics.Division', on_delete=models.CASCADE, related_name='students')
    admission_date = models.DateField(default=timezone.now)

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['standard__order_index', 'division__name', 'roll_number', 'full_name']
        constraints = [
            models.UniqueConstraint(fields=['school', 'gr_number'], name='unique_school_student_gr_number'),
            models.UniqueConstraint(
                fields=['school', 'academic_year', 'division', 'roll_number'],
                condition=models.Q(roll_number__isnull=False, is_active=True),
                name='unique_active_roll_per_division_year'
            ),
        ]
```

### B. `StudentTransferRequest` Model (`apps/students/models.py`)
```python
class StudentTransferRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    school = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='student_transfer_requests')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='transfer_requests')
    from_division = models.ForeignKey('academics.Division', on_delete=models.CASCADE, related_name='outgoing_transfers')
    to_division = models.ForeignKey('academics.Division', on_delete=models.CASCADE, related_name='incoming_transfers')
    requested_by = models.ForeignKey('faculty.Faculty', on_delete=models.CASCADE, related_name='requested_transfers')
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_transfers')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
```

---

## 3. Authentication & Student Portal Pipeline

### Dual-Identifier Authentication Backend
1. When a user submits `TenantLoginForm`:
   - If identifier contains `@` (e.g. `admin@school.com`): authenticate using email and password.
   - If identifier does NOT contain `@` (e.g. `10452` or `GR-2026-01`): lookup student by `gr_number=identifier, school=request.tenant, is_active=True`, find linked `student.user`, and verify password.
2. Default User creation for Students:
   - Email format: `gr_{school_code}_{gr_number}@student.local` (internal placeholder satisfying email uniqueness).
   - Username: `gr_{school_code}_{gr_number}`.
   - Role: `User.Role.STUDENT`.
   - Default Password: `Admin@123`.

### Tenant Dashboard Routing
In `apps/accounts/views.py`:
- `User.Role.SCHOOL_ADMIN` → `AdminDashboardView`
- `User.Role.FACULTY` → `FacultyDashboardView`
- `User.Role.STUDENT` → `StudentPortalView` (`/students/portal/`)

---

## 4. Scoped Permissions & Role Matrix

| Action | School Admin | Class Teacher (Assigned) | Non-Class Teacher / Super Admin |
|---|---|---|---|
| **View Students** | All classes/divisions | Assigned division only | Forbidden (403) |
| **Add Student** | Any class (enters GR No) | Assigned class only (enters GR No) | Forbidden (403) |
| **Edit Student** | All fields (including GR No) | Name/Roll/Parent info (GR No locked) | Forbidden (403) |
| **Transfer Request** | Direct division reassignment | Initiates transfer request | Forbidden (403) |
| **Approve Transfer** | 1-click Approve / Reject | View status only | Forbidden (403) |
| **Soft Delete** | Toggle active/inactive | Cannot delete | Forbidden (403) |

---

## 5. Don't Hand-Roll & Common Pitfalls

| Pitfall | Why Dangerous | Mitigation |
|---|---|---|
| **Hard-deleting student records** | Breaks historical attendance and grade audit trails | Enforce soft-delete via `is_active=False` |
| **Class Teacher bypassing division scope** | Malicious POST with another division ID | Validate `target_division == faculty.assigned_division` on backend |
| **GR Number collision across schools** | Duplicate GR numbers are common in different schools | Scope uniqueness strictly per school (`UniqueConstraint(fields=['school', 'gr_number'])`) |
| **Native browser `confirm()` popups** | Inconsistent look & feel violating Apple design system | Use in-modal Apple confirmation dialogs (`modal-confirm-delete`) |
| **Tenant context leakage in test suite** | Fails subsequent unit tests across apps | Call `set_current_tenant(None)` in `tearDown()` of all student test suites |

---

## 6. Verification & Test Plan

1. **Model & Constraint Unit Tests**:
   - Verify GR Number uniqueness per school tenant.
   - Verify roll number uniqueness within standard + division + academic year.
   - Verify soft-delete behavior.
2. **Authentication & User Provisioning Tests**:
   - Verify Student User created with `Role.STUDENT` and default password `Admin@123`.
   - Verify Student login via GR Number and redirection to `/students/portal/`.
   - Verify password verification for students and email login for staff.
3. **Scoped CRUD Permission Tests**:
   - School Admin can create and edit students across all classes with editable GR Number.
   - Class Teacher can only create/edit students in their assigned division.
   - Class Teacher attempt to edit GR Number is rejected or ignored.
   - Unassigned Faculty is blocked (403 Forbidden).
4. **Transfer Request Workflow Tests**:
   - Class Teacher creates transfer request for student in their division.
   - School Admin approves transfer request: student's division updates atomically.
   - School Admin rejects transfer request: student's division remains unchanged.
5. **Student Portal Read-Only Tests**:
   - Authenticated student can view their personal details, assigned Class Teacher, and enrolled subjects with respective subject teachers.
   - Student cannot access administrative or faculty endpoints (403 Forbidden).
