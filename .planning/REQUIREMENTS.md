# Requirements: Milestone v3.0 (Academic Structure & Bulk Excel Onboarding)

## Academic Structure & Master Data (ACAD)
- [ ] **ACAD-01**: Admin can create and manage Academic Years with an `is_current` active session indicator per tenant.
- [ ] **ACAD-02**: Admin can create, edit, list, and delete Standards (Grades 1 to 12 / Pre-primary).
- [ ] **ACAD-03**: Admin can create, edit, list, and delete Divisions (Sections A, B, C, etc.) linked to Standards and Academic Years.
- [ ] **ACAD-04**: Admin can create, edit, list, and delete Subjects (e.g., Mathematics, Science, English, Gujarati, Hindi, Social Science) with subject codes.

## Teacher Allocations & Mappings (ALLOC)
- [ ] **ALLOC-01**: Admin can assign a single Faculty member as the Class Teacher for a Standard+Division (1-to-1 mapping per Academic Year).
- [ ] **ALLOC-02**: Admin can allocate Subject Teachers to specific Standard+Division+Subject combinations.
- [ ] **ALLOC-03**: System enforces uniqueness and prevents conflicting double allocations.

## Student Management, Scoped CRUD & Student Portal (STU)
- [ ] **STU-01**: School Admin has full CRUD across all students in all classes, including GR Number edits and active/inactive status toggling.
- [ ] **STU-02**: Class Teacher has scoped CRUD access strictly for students in their assigned class/division, with GR Number field locked/read-only.
- [ ] **STU-03**: Class Teacher can submit a Student Class Transfer Request for Principal approval.
- [ ] **STU-04**: Student soft-delete mechanism (`is_active=False`) preserves historical integrity.
- [ ] **STU-05**: Responsive Apple-style UI table with search by GR No / Name / Roll No and filter by Standard/Division.
- [ ] **STU-06**: Student Portal Login — Students can log in using GR Number and default password `Admin@123`, viewing only their personal profile, assigned class, class teacher, and subjects.

## Bulk Excel/CSV Onboarding Engine (BULK)
- [ ] **BULK-01**: Downloadable sample Excel (`.xlsx`) and CSV (`.csv`) templates with instructions and dummy sample rows for all 4 import stages.
- [ ] **BULK-02**: Step 1 Faculty Bulk Import — uploads teachers list, checks duplicate emails/employee codes, previews data with status badges, and creates User accounts with default password `Admin@123`.
- [ ] **BULK-03**: Step 2 Class & Class Teacher Bulk Import — creates Standards, Divisions, and assigns Class Teachers with validation preview and atomic commit.
- [ ] **BULK-04**: Step 3 Subject Teacher Mapping Bulk Import — creates Subject Teacher allocations with dependency checks on existing classes and teachers.
- [ ] **BULK-05**: Step 4 Student Bulk Import — uploads student roster with unique GR Number checks, standard/division linking, roll number validation, auto-creates Student User accounts (`username` = GR No, default password = `Admin@123`), preview table, and atomic commit.

## Faculty Portal Experience & Security (FAC / AUTH)
- [ ] **FAC-01**: "My Class" dashboard for Class Teachers displaying assigned students, quick parent contact, and "+ Add Student" modal.
- [ ] **FAC-02**: "My Subjects" view for Subject Teachers showing their assigned classes, subjects, and student rosters (read-only).
- [ ] **AUTH-01**: Faculty and Student self-service password change and profile management.
- [ ] **SEC-01**: Backend multi-tenant and role-based permission decorators preventing cross-tenant and cross-class unauthorized modifications.

---

## Traceability Matrix

| Requirement | Phase | Status |
|-------------|-------|--------|
| ACAD-01, ACAD-02, ACAD-03, ACAD-04, ALLOC-01, ALLOC-02, ALLOC-03 | Phase 1 | Pending |
| STU-01, STU-02, STU-03, STU-04, STU-05, STU-06 | Phase 2 | Pending |
| BULK-01, BULK-02, BULK-03, BULK-04, BULK-05 | Phase 3 | Pending |
| FAC-01, FAC-02, AUTH-01, SEC-01 | Phase 4 | Pending |
