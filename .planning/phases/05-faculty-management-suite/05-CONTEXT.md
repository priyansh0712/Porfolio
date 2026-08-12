# Phase 5 Context: Faculty Management Suite

## Phase Scope
Provide School Admins with comprehensive faculty management capabilities (create, update, deactivate, list view) scoped to their tenant.

---

## Decisions & Locked Choices

### 1. Data Model & Employee Code Assignment
- **Employee Code Pattern**: Auto-generate Employee Code using format `[SUBDOMAIN-UPPER]-FAC-[NUMBER]` (e.g. `GREENWOOD-FAC-001`) with optional manual override by School Admin.
- **Uniqueness**: Employee Code must be strictly unique within the active school tenant.
- **Fields**:
  - `first_name`, `last_name`
  - `email`, `phone_number`
  - `employee_code` (auto-generated or manual override)
  - `department` (e.g. Science, Mathematics, English, Administration)
  - `designation` (e.g. Senior Teacher, Assistant Teacher, HOD)
  - `date_joined`
  - `is_active` (boolean, default True)
  - `user` (FK to User account, null=True, on_delete=SET_NULL)
  - `school` (FK to School tenant, on_delete=CASCADE)

### 2. User Account Integration
- **Auto-create User**: When a new Faculty profile is created, automatically initialize a linked `User` account with `role = FACULTY` and `school = active_tenant`.
- **Authentication**: Email serves as primary username identifier.
- **Deactivation**: Deactivating a Faculty member disables their linked `User` account (`is_active = False`) and prevents check-in / login without removing historical attendance logs.

### 3. UI Layout & Apple Design System Contract
- **View Type**: Apple-styled Data Table (`#f5f5f7` canvas, `#ffffff` card containers, 1px hairline borders).
- **Header & Controls**:
  - Search Bar (real-time live filter by name, email, employee code).
  - Department Dropdown Filter.
  - Status Filter (`All`, `Active`, `Inactive`).
  - "+ Add Faculty" Primary Blue Action Pill Button (`#0066cc`).
- **Table Columns**:
  1. Faculty Name & Email
  2. Employee Code
  3. Department & Designation
  4. Status Badge (`Active` green, `Inactive` gray)
  5. Face Enrollment Badge (`Pending` amber / `Enrolled` blue — prepared for Phase 6)
  6. Actions (`Edit`, `Toggle Active/Inactive`)
- **Modals / Drawers**: Add/Edit Faculty form inside an Apple modal with backdrop blur and smooth transitions.

---

## Next Steps
- Execute `/gsd-plan-phase 5` to break down Phase 5 into detailed execution plans (`05-01` and `05-02`).
