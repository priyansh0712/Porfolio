# Phase 5 Context: Faculty Management Suite

## Phase Scope
Provide School Admins with comprehensive faculty management capabilities (create, update, deactivate, list view) scoped to their tenant.

---

## Decisions & Locked Choices

### 1. Data Model & Employee Code Assignment
- **Email Uniqueness**: `Faculty.email` is **globally unique** (`unique=True`), matching `User.email` to maintain global authentication consistency and eliminate account resolution ambiguity across tenants.
- **Employee Code Pattern**: Auto-generate Employee Code using format `[SUBDOMAIN-UPPER]-FAC-[NUMBER]` (e.g. `GREENWOOD-FAC-001`) with optional manual override by School Admin.
- **Production Sequence Counter (DB Row Locking)**: Uses a dedicated `TenantSequence` model (or tenant sequence counter) with PostgreSQL `select_for_update()` row-level locking inside `@transaction.atomic`. This guarantees 100% race-condition safety, zero sequence gaps, and predictable scalability.
- **Uniqueness**: Employee Code must be strictly unique within the active school tenant.
- **Fields**:
  - `first_name`, `last_name`
  - `email` (`EmailField(unique=True)`)
  - `phone_number`
  - `employee_code` (auto-generated or manual override)
  - `department` (e.g. Science, Mathematics, English, Administration)
  - `designation` (e.g. Senior Teacher, Assistant Teacher, HOD)
  - `date_joined`
  - `is_active` (boolean, default True)
  - `user` (`OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)` — **SET_NULL preserves faculty profile & historical logs even if User is removed**)
  - `school` (`ForeignKey(School, on_delete=models.CASCADE)`)

### 2. User Account Integration & Login Boundary
- **Identity Provider Only**: When a Faculty record is created, initialize a linked `User` account with `role = FACULTY` and `school = active_tenant`.
- **No Password Login for Faculty**: Faculty accounts use `set_unusable_password()`. Faculty members are NOT permitted to log into the web dashboard using traditional email/password. Web dashboard access is strictly for `SCHOOL_ADMIN` and `SUPER_ADMIN`.
- **Identity Guard**: `TenantAwareAuthBackend` and `TenantLoginView` reject `FACULTY` role from web login, preserving face recognition as the sole authentication mechanism for faculty check-in/check-out.
- **Deactivation**: Deactivating a Faculty member disables their linked `User` account (`is_active = False`) without deleting any historical attendance records.

### 3. 3-Layer Defense-In-Depth Security Protocol
Security for ALL Faculty CRUD views follows the project's strict 3-Layer Defense-In-Depth:
1. **Layer 1 (Middleware)**: `TenantRoleAccessMiddleware` fast-fails unauthenticated/mismatched role requests.
2. **Layer 2 (View Permission)**: `SchoolAdminRequiredMixin` enforces active `SCHOOL_ADMIN` role and matches `user.school == request.tenant`.
3. **Layer 3 (Explicit Query & DB Scoping)**: Views explicitly query `Faculty.objects.filter(school=request.tenant, pk=pk)` and handle HTTP 404/403. Object-level validation prevents URL ID manipulation attacks across tenants.
4. **DB Security**: Database `UniqueConstraint(fields=['school', 'employee_code'])`.

### 4. Face Enrollment Architecture (Phase 6 Ready)
- **Status Architecture Only**: The `Faculty` model includes an `is_face_enrolled` boolean property / field (default `False`).
- **Zero Fake Functionality**: Do NOT implement fake or mock enrollment logic in Phase 5. Phase 5 only provides the `Pending` (amber) / `Enrolled` (blue) status badge UI infrastructure. Phase 6 will wire up the actual InsightFace ArcFace vector extraction pipeline.

### 5. UI Layout & Apple Design System Contract
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
