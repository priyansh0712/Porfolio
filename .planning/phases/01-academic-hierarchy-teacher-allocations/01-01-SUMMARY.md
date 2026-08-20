# Plan 01-01 Summary: Backend Data Architecture, Models, Constraints & Security

**Phase:** 01-academic-hierarchy-teacher-allocations  
**Plan:** 01-01  
**Status:** Complete (12/12 Tests Passing)  
**Date:** 2026-08-20  

---

## Tasks Completed

1. **Created `apps.academics` app & configuration:**
   - Initialized `apps/academics/apps.py` (`AcademicsConfig`).
   - Registered `'apps.academics'` in `config/settings/base.py` `INSTALLED_APPS`.
   - Updated `TENANT_SCOPED_PREFIXES` in `apps/accounts/middleware.py` with `'/academics/'` to enforce Layer 1 security preventing Super Admin access.
2. **Defined Multi-Tenant Data Models with Constraints (`apps/academics/models.py`):**
   - `AcademicYear`: Multi-tenant session model with atomic single-active `is_current` toggle and date range validation.
   - `Standard`: Grades master (1-12, Nursery, UKG) with `order_index` sorting.
   - `Division`: Sections (A, B, C) attached to `Standard` with `models.PROTECT`.
   - `Subject`: Subjects with auto-uppercase unique `code` and Core vs Elective categorization.
   - `ClassTeacherAllocation`: 1-to-1 division to faculty mapping per academic year.
   - `SubjectTeacherAllocation`: 1-to-1 division+subject to faculty mapping per academic year.
   - Applied migration `0001_initial.py`.
3. **Forms & Business Logic Services:**
   - `apps/academics/forms.py`: Created `AcademicYearForm`, `StandardForm`, `DivisionForm`, `SubjectForm`, `ClassTeacherAllocationForm`, and `SubjectTeacherAllocationForm` with tenant-scoped querysets.
   - `apps/academics/services.py`: Implemented `get_current_academic_year`, `assign_class_teacher`, `assign_subject_teacher`, and `get_allocation_matrix`.
4. **Automated Unit Tests (`apps/academics/tests.py`):**
   - 12 comprehensive unit tests covering single-active year switching, standard ordering, uniqueness constraints, cross-tenant isolation, and inactive faculty assignment prevention.

---

## Verification

- `python manage.py test apps.academics` $\rightarrow$ **12 tests passed (OK)**.
