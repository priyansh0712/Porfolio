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

### 2. User Account Integration & Login Boundary (IMPORTANT)
- **Identity Provider Only**: When a Faculty record is created, initialize a linked `User` account with `role = FACULTY` and `school = active_tenant`.
- **No Password Login for Faculty**: Faculty accounts use `set_unusable_password()`. Faculty members are NOT permitted to log into the web dashboard using traditional email/password. Web dashboard access is strictly for `SCHOOL_ADMIN` and `SUPER_ADMIN`.
- **Identity Guard**: `TenantAwareAuthBackend` / `TenantLoginView` must block `FACULTY` role from web dashboard login, preserving face recognition as the sole authentication mechanism for faculty check-in/check-out.
- **Deactivation**: Deactivating a Faculty member disables their linked `User` account (`is_active = False`) without deleting any historical attendance records.

### 3. Face Enrollment Architecture (Phase 6 Ready)
- **Status Architecture Only**: The `Faculty` model includes an `is_face_enrolled` boolean property / field (default `False`).
- **Zero Fake Functionality**: Do NOT implement fake or mock enrollment logic in Phase 5. Phase 5 only provides the `Pending` (amber) / `Enrolled` (blue) status badge UI infrastructure. Phase 6 will wire up the actual InsightFace ArcFace vector extraction pipeline.

### 4. UI Layout & Apple Design System Contract
- **View Type**: Apple-styled Data Table (`#f5f5f7` canvas, `#ffffff` card containers, 1px hairline borders). Optimized for 50–500 faculty management.
- **Header & Controls**:
  - Search Bar (real-time live filter by name, email, employee code).
  - Department Dropdown Filter (dynamic per tenant).
  - Status Filter (`All`, `Active`, `Inactive`).
  - "+ Add Faculty" Primary Blue Action Pill Button (`#0066cc`).
- **Table Columns**:
  1. Faculty Name & Email
  2. Employee Code
  3. Department & Designation
  4. Status Badge (`Active` green, `Inactive` gray)
  5. Face Enrollment Status (`Pending` amber badge — ready for Phase 6)
  6. Actions (`Edit`, `Toggle Active/Inactive`)
- **Modals / Drawers**: Add/Edit Faculty form inside an Apple modal with backdrop blur and smooth transitions.

---

## Next Steps
- Execute `/gsd-plan-phase 5` to break down Phase 5 into detailed execution plans (`05-01` and `05-02`).
