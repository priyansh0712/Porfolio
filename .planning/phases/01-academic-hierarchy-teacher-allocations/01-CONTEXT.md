# Phase 1: Academic Hierarchy & Teacher Allocations - Context

**Gathered:** 2026-08-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build foundational data models and School Admin management interfaces for:
1. Academic Years with active session (`is_current`) state management per school tenant.
2. Standards (Grades) and Divisions (Sections) master hierarchy with duplicate prevention.
3. Subjects master list with subject codes and core/elective types.
4. Class Teacher (1-to-1 per division per academic year) and Subject Teacher allocations with strict constraint validation.
5. Unified School Admin "Academics" hub with Apple Design System UI.

Student records, bulk Excel import wizards, and faculty personal dashboards belong in subsequent phases (Phases 2, 3, and 4).
</domain>

<decisions>
## Implementation Decisions

### Academic Year Structure & Active Session Handling (ACAD-01)
- **D-01:** Academic Years are defined with a descriptive label (e.g. `2026-2027`), `start_date`, `end_date`, and boolean `is_current`.
- **D-02:** Auto-deactivate others: When an Academic Year is flagged `is_current=True`, all other Academic Years for that school tenant are automatically updated to `is_current=False`.
- **D-03:** Navbar Session Switcher: School Admin header includes an Academic Year selector dropdown allowing admins to browse records for past/upcoming sessions while defaulting to the current active session.

### Standards & Divisions Master Setup (ACAD-02, ACAD-03)
- **D-04:** Standards support numeric grades (1-12) as well as pre-primary levels (Nursery, LKG, UKG) using `name` and `order_index` integer for natural chronological sorting.
- **D-05:** Master Standard -> Divisions: Divisions (e.g. "A", "B", "C", "Rose") are master records attached directly to a `Standard`. Teacher allocations and student enrollments link `Division` to `AcademicYear`.
- **D-06:** Deletion Protection: Standards, Divisions, and Subjects use `models.PROTECT` to prevent accidental deletion when referenced in teacher allocations or student records. Soft-toggling via `is_active` is supported.

### Subjects Master Setup (ACAD-04)
- **D-07:** Subjects include `name`, unique `code` per school (e.g. `MATH-01`, `ENG-01`), `subject_type` (Core vs Elective/Optional), and `is_active`. Unique constraint on `[school, code]`.

### Teacher Allocation Constraints (ALLOC-01, ALLOC-02, ALLOC-03)
- **D-08:** Class Teacher 1-to-1 Mapping: Strictly 1 Class Teacher per Standard + Division per Academic Year (`ClassTeacherAllocation` with DB unique constraint on `[school, academic_year, division]`). Faculty can be assigned across multiple classes if needed.
- **D-09:** Subject Teacher Allocation: Strictly 1 Primary Subject Teacher per Subject per Division per Academic Year (`SubjectTeacherAllocation` with DB unique constraint on `[school, academic_year, division, subject]`).
- **D-10:** Reassignment & Auto-replace: Admin can update or reassign teachers with confirmation, cleanly updating the allocation records and logging changes.
- **D-11:** Faculty Status Validation: Only active faculty members (`is_active=True`) from the tenant can be selected.

### School Admin UI & Navigation Layout
- **D-12:** Unified "Academics" Hub: Top-level "Academics" menu in the School Admin navigation bar featuring Apple-style segmented tabs:
  1. Academic Years
  2. Standards & Divisions
  3. Subjects
  4. Teacher Allocations
- **D-13:** Standard Cards with Inline Division Badges: Standards displayed as clean white cards with hairline borders (`#ffffff`, border `#e0e0e0`) featuring division badges and quick "+ Add Division" modals.
- **D-14:** Class-wise Grid / Matrix View for Allocations: Grouped by Standard & Division with a Class Teacher badge/selector and Subject Teacher allocation table.

### Antigravity's Discretion
- Modal animation transitions and Tailwind utility classes conforming to Apple Design System.
- Model Manager helper methods (e.g., `get_active_year(school)`).
- Specific form validation error messages, toasts, and empty state cards.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing:**

### Academic Requirements & Architecture
- `.planning/REQUIREMENTS.md` § Academic Structure & Master Data (ACAD-01 to ACAD-04, ALLOC-01 to ALLOC-03)
- `.planning/PROJECT.md` § Milestone v3.0 Scope & Core Value
- `.planning/ROADMAP.md` § Active Milestone v3.0 Phase 1

### UI & Styling System
- `DESIGN-apple.md` — Apple Design System specification (colors, canvas `#f5f5f7`, typography, buttons, tables, cards)
- `.agents/AGENTS.md` — Apple Design System rules and constraints
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps.tenants.models.TenantModel`: Base model for all multi-tenant tables (`school` foreign key with DB indexes).
- `apps.faculty.models.Faculty`: Tenant-scoped faculty model for teacher assignments.
- `templates/layouts/admin_base.html`: Main authenticated School Admin layout with top navbar, notifications, and container.
- `apps.core.decorators`: Multi-tenant and role-based access decorators (`@tenant_admin_required`).

### Established Patterns
- Multi-tenancy: Subdomain-based resolution via middleware; all querysets scoped by `request.tenant`.
- Forms & Validation: Clean Django forms with inline field errors and CSRF token protection.
- Styling: Tailwind CSS utility classes adhering to Apple Parchment `#f5f5f7` canvas, SF Pro typography, and Apple Blue `#0066cc` buttons.

### Integration Points
- Create new Django app `apps/academics/`.
- Register `apps.academics` in `config/settings/base.py` `INSTALLED_APPS`.
- Include `apps.academics.urls` in `config/urls.py` under tenant routing.
- Add "Academics" link to School Admin navigation header in `templates/includes/admin_header.html`.
</code_context>

<specifics>
## Specific Ideas
- Clean, Apple-styled segmented navigation pills for switching between Academic Years, Standards & Divisions, Subjects, and Allocations.
- Modal popups for quick additions (e.g. quick-adding a division "B" under "Standard 10" without leaving the page).
- Allocation Matrix that makes it immediately obvious which classes are missing a Class Teacher or Subject Teachers.
</specifics>

<deferred>
## Deferred Ideas
- Student Master Records, GR Number tracking, and Student Portal (Phase 2).
- 4-Step Excel/CSV Bulk Import Wizard for Teachers, Classes, Subjects, and Students (Phase 3).
- Dedicated "My Class" and "My Subjects" dashboards for Faculty members (Phase 4).
</deferred>

---

*Phase: 01-academic-hierarchy-teacher-allocations*
*Context gathered: 2026-08-20*
