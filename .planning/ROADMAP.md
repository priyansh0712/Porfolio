# Roadmap: School Faculty Attendance & Academic Management (StudentERP1)

## Shipped Milestones

- **v1.0 Face Recognition Attendance Platform**: Shipped 2026-08-15. Core multi-tenant webcam face scanning, working schedule engine, and admin reports (121 tests passing).
- **v2.0 Leave Management & Faculty Dashboard**: Shipped 2026-08-16. Faculty leave requests, balance tracking, approvals, calendar exclusions, and personal dashboards (159 tests passing).
- **v3.0 Academic Structure & Bulk Excel Onboarding**: Shipped 2026-08-21. Academic Standards, Divisions, Subjects, Student Roster CRUD, 4-step Excel/CSV wizard, teacher dashboards, password security (246 tests passing).

---

## Active Milestone: v3.0 Academic Structure & Bulk Excel Onboarding (SHIPPED)

**Goal:** Provide schools with complete academic management (Standards, Divisions, Subjects) and a 4-step Excel/CSV bulk import wizard to easily onboard Faculty, Class Teachers, Subject Teachers, and Students with automatic mapping, student login portals, and role-based permissions.

### Phase 1: Academic Hierarchy & Teacher Allocations (Completed 2026-08-21)
**Goal:** Build data models and management views for Academic Years, Standards, Divisions, Subjects, and 1-to-1 Class Teacher & Subject Teacher allocations.
- **Requirements:** `ACAD-01`, `ACAD-02`, `ACAD-03`, `ACAD-04`, `ALLOC-01`, `ALLOC-02`, `ALLOC-03`

### Phase 2: Student Master Records, Scoped CRUD & Student Portal (Completed 2026-08-21)
**Goal:** Build Student models with unique GR numbers, soft-delete mechanisms, role-based CRUD permissions (Principal full access, Class Teacher scoped access with locked GR numbers), and Student Portal Login (Username = GR No, default password = `Admin@123`).
- **Requirements:** `STU-01`, `STU-02`, `STU-03`, `STU-04`, `STU-05`, `STU-06`

### Phase 3: 4-Step Bulk Excel/CSV Onboarding Engine (Completed 2026-08-21)
**Goal:** Implement 4-step sequential bulk import wizard (`.xlsx` & `.csv`) with downloadable templates, data validation preview tables, and atomic database commits.
- **Requirements:** `BULK-01`, `BULK-02`, `BULK-03`, `BULK-04`, `BULK-05`

### Phase 4: Faculty & Student Views, Password Security & Integration Polish (Completed 2026-08-21)
**Goal:** Provide faculty with dedicated "My Class" and "My Subjects" dashboards, self-service password changing for faculty and students, and end-to-end security test verification.
- **Requirements:** `FAC-01`, `FAC-02`, `AUTH-01`, `SEC-01`
