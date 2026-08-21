# Roadmap: School Faculty Attendance & Academic Management (StudentERP1)

## Shipped Milestones

- **v1.0 Face Recognition Attendance Platform**: Shipped 2026-08-15. Core multi-tenant webcam face scanning, working schedule engine, and admin reports (121 tests passing).
- **v2.0 Leave Management & Faculty Dashboard**: Shipped 2026-08-16. Faculty leave requests, balance tracking, approvals, calendar exclusions, and personal dashboards (159 tests passing).

---

## Active Milestone: v3.0 Academic Structure & Bulk Excel Onboarding

**Goal:** Provide schools with complete academic management (Standards, Divisions, Subjects) and a 4-step Excel/CSV bulk import wizard to easily onboard Faculty, Class Teachers, Subject Teachers, and Students with automatic mapping, student login portals, and role-based permissions.

### Phase 1: Academic Hierarchy & Teacher Allocations
**Goal:** Build data models and management views for Academic Years, Standards, Divisions, Subjects, and 1-to-1 Class Teacher & Subject Teacher allocations.
- **Requirements:** `ACAD-01`, `ACAD-02`, `ACAD-03`, `ACAD-04`, `ALLOC-01`, `ALLOC-02`, `ALLOC-03`
- **Success Criteria:**
  1. School Admin can create and switch Active Academic Years per tenant (`is_current=True`).
  2. School Admin can create, edit, list, and delete Standards, Divisions, and Subjects with duplicate prevention.
  3. School Admin can assign Class Teachers and Subject Teachers with strict validation.

### Phase 2: Student Master Records, Scoped CRUD & Student Portal
**Goal:** Build Student models with unique GR numbers, soft-delete mechanisms, role-based CRUD permissions (Principal full access, Class Teacher scoped access with locked GR numbers), and Student Portal Login (Username = GR No, default password = `Admin@123`).
- **Requirements:** `STU-01`, `STU-02`, `STU-03`, `STU-04`, `STU-05`, `STU-06`
- **Success Criteria:**
  1. Principal can create, search, filter, view, edit (including GR No), and soft-delete students.
  2. Class Teacher can create and edit students ONLY within their assigned class with GR Number locked/read-only.
  3. Class Teacher can submit class transfer requests and Principal can approve/reject them.
  4. Students can log in with their GR Number and view their personal academic profile (read-only).

### Phase 3: 4-Step Bulk Excel/CSV Onboarding Engine (Completed 2026-08-21)
**Goal:** Implement 4-step sequential bulk import wizard (`.xlsx` & `.csv`) with downloadable templates, data validation preview tables, and atomic database commits.
- **Requirements:** `BULK-01`, `BULK-02`, `BULK-03`, `BULK-04`, `BULK-05`
- **Success Criteria:**
  1. Admin can download sample Excel/CSV templates with instructions and dummy data for all 4 steps.
  2. Step 1 imports teachers and creates user accounts with default password `Admin@123`.
  3. Steps 2 & 3 import class divisions and subject mappings with dependency checks.
  4. Step 4 imports students with duplicate GR No checks, auto-creates student login accounts, and shows an interactive validation preview before atomic commit.

### Phase 4: Faculty & Student Views, Password Security & Integration Polish (Completed 2026-08-21)
**Goal:** Provide faculty with dedicated "My Class" and "My Subjects" dashboards, self-service password changing for faculty and students, and end-to-end security test verification.
- **Requirements:** `FAC-01`, `FAC-02`, `AUTH-01`, `SEC-01`
- **Success Criteria:**
  1. Class Teachers can access their assigned class roster and quick-add student modal via "My Class".
  2. Subject Teachers can view their assigned class rosters (read-only) via "My Subjects".
  3. Faculty and Students can update their passwords and profile details upon login.
  4. 100% automated test suite passes with full multi-tenant and role security verification.
