# Phase 1: Academic Hierarchy & Teacher Allocations - Research

**Phase:** 01-academic-hierarchy-teacher-allocations  
**Milestone:** v3.0 (Academic Structure & Bulk Excel Onboarding)  
**Requirements Covered:** `ACAD-01`, `ACAD-02`, `ACAD-03`, `ACAD-04`, `ALLOC-01`, `ALLOC-02`, `ALLOC-03`  
**Status:** Complete & Prescriptive  

---

## Executive Summary & Phase Scope

Phase 1 provides the foundational academic data architecture and school administrative management interfaces for:
1. **Academic Years (`ACAD-01`)**: Multi-tenant academic session management with automated `is_current` single-active enforcement per tenant and header-based session browsing.
2. **Standards Master (`ACAD-02`)**: Numeric (Grades 1-12) and pre-primary (Nursery, LKG, UKG) grades with natural ordering via `order_index`.
3. **Divisions Master (`ACAD-03`)**: Class divisions/sections (e.g., A, B, C, Rose) attached to Standards, with duplicate constraint enforcement.
4. **Subjects Master (`ACAD-04`)**: School subjects with standardized uppercase subject codes (e.g. `MATH-01`) and Core vs. Elective categorization.
5. **Teacher Allocations (`ALLOC-01`, `ALLOC-02`, `ALLOC-03`)**:
   - **Class Teacher Mapping (1-to-1):** Strictly 1 Class Teacher per Division per Academic Year.
   - **Subject Teacher Mapping (1-to-1):** Strictly 1 Primary Subject Teacher per Division per Subject per Academic Year.
   - Strict database unique constraints, auto-replacement handling, and tenant-boundary isolation.
6. **School Admin Academic Hub UI**: Unified Apple Design System interface (`/academics/`) with segmented tab controls, standard cards with inline division pills, modal CRUD operations, and an allocation matrix grid.

---

## Standard Stack

| Layer | Component / Library | Purpose | Rationale / Prescriptions |
|---|---|---|---|
| **Backend Framework** | Django 5.1+ / Python 3.12+ | Core ORM, views, forms, migrations | Native Django CBVs with `SchoolAdminRequiredMixin`. |
| **Multi-Tenancy** | `apps.tenants.models.TenantModel` & `TenantManager` | Data isolation per school tenant | All models (`AcademicYear`, `Standard`, `Division`, `Subject`, `ClassTeacherAllocation`, `SubjectTeacherAllocation`) inherit `TenantModel`. All queries auto-scoped by `request.tenant`. |
| **Database** | PostgreSQL / SQLite (dev) | Relational storage & constraints | `UniqueConstraint` on `[school, name]`, `[school, code]`, `[school, academic_year, division]`, and `[school, academic_year, division, subject]`. |
| **UI Styling** | Tailwind CSS + Apple Design System | Frontend presentation | Pure Apple aesthetics: `#f5f5f7` canvas, `#ffffff` cards with hairline border (`#e0e0e0`), Apple Action Blue (`#0066cc`), SF Pro typography. |
| **Interactivity** | Vanilla JavaScript (ES6+) | Modal controls, tab switching, dynamic filters | Lightweight, zero-framework DOM manipulation for modal show/hide and allocation quick-save. |
| **Testing** | `django.test.TestCase` / `pytest-django` | Automated verification | Unit tests for multi-tenant isolation, unique constraints, atomic session switching, and role-based permissions. |

---

## Architecture Patterns

### 1. Dedicated Django App Structure (`apps/academics/`)
All academic models, views, forms, and URLs reside in a new, self-contained app:
```
apps/academics/
├── __init__.py
├── apps.py                 # AcademicsConfig
├── models.py               # AcademicYear, Standard, Division, Subject, ClassTeacherAllocation, SubjectTeacherAllocation
├── forms.py                # AcademicYearForm, StandardForm, DivisionForm, SubjectForm, AllocationForm
├── views.py                # AcademicHubView, AcademicYearViews, StandardViews, DivisionViews, SubjectViews, AllocationViews
├── urls.py                 # App URL routing
├── services.py             # AcademicService (session resolution, allocation helpers)
└── tests.py                # Comprehensive multi-tenant & constraint test suite
```

### 2. Single Active Academic Session Engine (`is_current`)
Each school tenant must have at most one active Academic Year (`is_current=True`).
- **Atomic Enforcement in Model `save()`:**
  ```python
  @transaction.atomic
  def save(self, *args, **kwargs):
      if self.is_current:
          # Automatically deactivate all other academic years for this school tenant
          AcademicYear.objects.filter(school=self.school, is_current=True).exclude(pk=self.pk).update(is_current=False)
      super().save(*args, **kwargs)
  ```
- **Session Helper / Manager:**
  ```python
  @classmethod
  def get_current_year(cls, school):
      return cls.objects.filter(school=school, is_current=True).first()
  ```

### 3. Allocation Data Model & Uniqueness Hierarchy
- **Standard $\rightarrow$ Division Master Hierarchy:**
  - `Standard` represents the grade level (e.g., `Standard 10`, `order_index=10`).
  - `Division` belongs to `Standard` (e.g., `Division A` of `Standard 10`).
  - Standards and Divisions are persistent master entities (not recreated every academic year).
- **Academic Year Bindings:**
  - `ClassTeacherAllocation` binds `(school, academic_year, division) -> faculty`.
  - `SubjectTeacherAllocation` binds `(school, academic_year, division, subject) -> faculty`.
  - Both use `models.PROTECT` on `division`, `subject`, and `faculty` foreign keys to prevent accidental cascading destruction of historical records.

### 4. 3-Layer Security Integration
- **Layer 1 (Middleware):** Add `'/academics/'` to `TENANT_SCOPED_PREFIXES` in `apps/accounts/middleware.py` so Platform Super Admin is blocked from viewing or modifying tenant academic data (AUTH-02 boundary).
- **Layer 2 (View Mixins):** All views enforce `SchoolAdminRequiredMixin`.
- **Layer 3 (ORM Scoping):** All model operations and forms strictly scope queries by `request.tenant`.

---

## Don't Hand-Roll

| Problem | Anti-Pattern (Don't Do This) | Standard Solution (Do This) |
|---|---|---|
| **Multi-Tenancy Filtering** | Writing custom `school_id = request.user.school_id` in every raw query | Inherit `TenantModel` and use `TenantManager`, which automatically filters queries to `request.tenant` via contextvars. |
| **Single Active Year Enforcement** | Looping through records in the frontend or view | Enforce in `AcademicYear.save()` inside `transaction.atomic` using `AcademicYear.objects.filter(school=self.school).exclude(pk=self.pk).update(is_current=False)`. |
| **Allocation Conflict Handling** | Catching generic Python exceptions or checking in JS | Use DB `models.UniqueConstraint` with clear constraint names, combined with `update_or_create` in views/services. |
| **Delete Cascades on Referenced Data** | Using `on_delete=models.CASCADE` on master entities (Standards, Divisions, Subjects) | Use `on_delete=models.PROTECT` on allocations so deletions are safely blocked with a user-friendly error message, offering `is_active=False` toggle instead. |
| **Sorting of Standards** | Alphabetical sorting (which makes "Standard 10" come before "Standard 2") | Use an integer `order_index` field (e.g., Nursery=0, LKG=1, UKG=2, Std 1=3 ... Std 12=14) and set `ordering = ['order_index', 'name']`. |

---

## Common Pitfalls & Edge Cases

1. **Cross-Tenant Faculty Selection in Allocation Forms:**
   - *Pitfall:* Standard ModelChoiceField loading all faculty members across all schools.
   - *Fix:* In `AllocationForm.__init__()`, restrict queryset: `self.fields['faculty'].queryset = Faculty.objects.filter(school=tenant, is_active=True)`.
2. **First-Time School Setup with Zero Academic Years:**
   - *Pitfall:* Academic Hub crashing if `get_current_year()` returns `None`.
   - *Fix:* Render a prominent "Welcome! Create your first Academic Year to get started" Apple-style banner with a "+ New Academic Year" CTA.
3. **Session Switching vs Current Active Session:**
   - *Pitfall:* Admin switches dropdown to view "2025-2026" and mistakenly alters the tenant's global `is_current` setting.
   - *Fix:* Browsing year is stored in URL query params (`?year=<id>`) or session, separate from the persistent DB boolean `is_current=True`.
4. **Duplicate Subject Codes within Tenant:**
   - *Pitfall:* Different casing like `math-01` vs `MATH-01` bypassing uniqueness.
   - *Fix:* Auto-capitalize subject code in `clean()` and `clean_code()` before validation and save.
5. **Class Teacher Reassignment:**
   - *Pitfall:* Assigning a new teacher to a class fails because a `ClassTeacherAllocation` already exists.
   - *Fix:* Use `ClassTeacherAllocation.objects.update_or_create(school=tenant, academic_year=year, division=division, defaults={'faculty': new_faculty})`.

---

## Code Examples & Reference Implementation Patterns

### 1. Data Models (`apps/academics/models.py`)
```python
from django.db import models, transaction
from django.core.exceptions import ValidationError
from apps.tenants.models import TenantModel


class AcademicYear(TenantModel):
    name = models.CharField(max_length=50, help_text="e.g. 2026-2027")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'name'],
                name='unique_academic_year_name_per_school'
            )
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({'end_date': 'End date must be after start date.'})

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.clean()
        if self.is_current:
            AcademicYear.objects.filter(school=self.school, is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}{' (Active)' if self.is_current else ''}"


class Standard(TenantModel):
    name = models.CharField(max_length=50, help_text="e.g. Standard 10, Grade 1, UKG")
    order_index = models.PositiveIntegerField(default=0, help_text="Order for sorting (0, 1, 2...)")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order_index', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'name'],
                name='unique_standard_name_per_school'
            )
        ]

    def __str__(self):
        return self.name


class Division(TenantModel):
    standard = models.ForeignKey(Standard, on_delete=models.PROTECT, related_name='divisions')
    name = models.CharField(max_length=20, help_text="e.g. A, B, C, Rose")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['standard__order_index', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'standard', 'name'],
                name='unique_division_per_standard_per_school'
            )
        ]

    def __str__(self):
        return f"{self.standard.name} - {self.name}"


class Subject(TenantModel):
    class SubjectType(models.TextChoices):
        CORE = 'CORE', 'Core Subject'
        ELECTIVE = 'ELECTIVE', 'Elective / Optional'

    name = models.CharField(max_length=100, help_text="e.g. Mathematics, Science")
    code = models.CharField(max_length=30, help_text="e.g. MATH-01")
    subject_type = models.CharField(max_length=20, choices=SubjectType.choices, default=SubjectType.CORE)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'code'],
                name='unique_subject_code_per_school'
            )
        ]

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.strip().upper()

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassTeacherAllocation(TenantModel):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='class_teacher_allocations')
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name='class_teacher_allocations')
    faculty = models.ForeignKey('faculty.Faculty', on_delete=models.PROTECT, related_name='class_teacher_allocations')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'academic_year', 'division'],
                name='unique_class_teacher_per_division_year'
            )
        ]

    def clean(self):
        super().clean()
        if self.faculty and self.faculty.school_id != self.school_id:
            raise ValidationError({'faculty': 'Faculty member must belong to the same school tenant.'})
        if self.faculty and not self.faculty.is_active:
            raise ValidationError({'faculty': 'Cannot assign an inactive faculty member.'})

    def __str__(self):
        return f"{self.academic_year.name}: {self.division} -> {self.faculty.full_name}"


class SubjectTeacherAllocation(TenantModel):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='subject_teacher_allocations')
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name='subject_teacher_allocations')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='subject_teacher_allocations')
    faculty = models.ForeignKey('faculty.Faculty', on_delete=models.PROTECT, related_name='subject_teacher_allocations')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'academic_year', 'division', 'subject'],
                name='unique_subject_teacher_per_division_subject_year'
            )
        ]

    def clean(self):
        super().clean()
        if self.faculty and self.faculty.school_id != self.school_id:
            raise ValidationError({'faculty': 'Faculty member must belong to the same school tenant.'})
        if self.faculty and not self.faculty.is_active:
            raise ValidationError({'faculty': 'Cannot assign an inactive faculty member.'})

    def __str__(self):
        return f"{self.academic_year.name}: {self.division} [{self.subject.name}] -> {self.faculty.full_name}"
```

### 2. URL Routing (`apps/academics/urls.py`)
```python
from django.urls import path
from apps.academics import views

app_name = 'academics'

urlpatterns = [
    path('', views.AcademicHubView.as_view(), name='hub'),
    
    # Academic Year CRUD
    path('years/create/', views.AcademicYearCreateView.as_view(), name='year_create'),
    path('years/<int:pk>/edit/', views.AcademicYearUpdateView.as_view(), name='year_edit'),
    path('years/<int:pk>/set-current/', views.AcademicYearSetCurrentView.as_view(), name='year_set_current'),
    path('years/<int:pk>/delete/', views.AcademicYearDeleteView.as_view(), name='year_delete'),
    
    # Standards CRUD
    path('standards/create/', views.StandardCreateView.as_view(), name='standard_create'),
    path('standards/<int:pk>/edit/', views.StandardUpdateView.as_view(), name='standard_edit'),
    path('standards/<int:pk>/delete/', views.StandardDeleteView.as_view(), name='standard_delete'),
    
    # Divisions CRUD
    path('divisions/create/', views.DivisionCreateView.as_view(), name='division_create'),
    path('divisions/<int:pk>/edit/', views.DivisionUpdateView.as_view(), name='division_edit'),
    path('divisions/<int:pk>/delete/', views.DivisionDeleteView.as_view(), name='division_delete'),
    
    # Subjects CRUD
    path('subjects/create/', views.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<int:pk>/edit/', views.SubjectUpdateView.as_view(), name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
    
    # Allocations
    path('allocations/class-teacher/', views.ClassTeacherAssignView.as_view(), name='assign_class_teacher'),
    path('allocations/subject-teacher/', views.SubjectTeacherAssignView.as_view(), name='assign_subject_teacher'),
    path('allocations/<int:pk>/delete-subject-teacher/', views.SubjectTeacherDeleteView.as_view(), name='delete_subject_teacher'),
]
```

---

## Verification & Testing Strategy

A dedicated test suite in `apps/academics/tests.py` must verify:

1. **Multi-Tenant Isolation:**
   - Queries from Tenant A never return Academic Years, Standards, Divisions, Subjects, or Allocations from Tenant B.
2. **Academic Year Logic:**
   - Setting an Academic Year `is_current=True` immediately and atomically sets all other years of that school to `is_current=False`.
   - Date validation rejects `end_date <= start_date`.
   - Name uniqueness enforced per school.
3. **Standards & Divisions Logic:**
   - Standards sort in ascending `order_index`.
   - Division uniqueness enforced within `[school, standard, name]`.
   - Protected deletion blocks deleting a Standard/Division if allocations exist.
4. **Subject Logic:**
   - Subject code uniqueness per school (case-insensitive uppercase normalized).
   - Core vs Elective choices work properly.
5. **Teacher Allocation Rules:**
   - 1 Class Teacher per division per year constraint: assigning a new teacher updates or replaces cleanly.
   - 1 Subject Teacher per division+subject per year constraint: duplicate assignments raise validation/constraint errors.
   - Cross-tenant teacher assignment rejected with `ValidationError`.
   - Inactive teacher assignment rejected with `ValidationError`.
6. **Security & Authorization:**
   - Super Admin accessing `/academics/` returns HTTP 403 (Layer 1 + Layer 2).
   - Unauthenticated requests redirect to `/login/`.
   - School Admin can perform full CRUD across their own tenant's academic hub.
