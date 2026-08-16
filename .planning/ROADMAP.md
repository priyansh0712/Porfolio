# Roadmap: School Faculty Attendance & Leave Management (StudentERP1 V2)

## Overview

This roadmap outlines the 9-phase sequence to implement the V2.0 features (Leave Management, Personal Faculty Dashboards, and In-App Notifications) as a clean extension of the validated V1.0 face attendance platform.

## Phases

- [x] **Phase 1: V2 Foundation & Database Models** - Create `leaves` and `notifications` apps, define models, run migrations, and write model-level unit tests.
- [x] **Phase 2: Excel Leave Allocation** - Excel upload utility, template download, validations, and admin leave upload UI.
- [x] **Phase 3: Faculty Dashboard, Login & Leave Requests** - Enable Faculty login, build Faculty dashboard layout, and implement Apply Leave form with validations.
- [x] **Phase 4: Admin Leave Review & Approval** - School Admin leave requests list, filters, and Approve/Reject controls with rejection reason validation.
- [x] **Phase 5: Leave-Attendance Integration** - Nullable check-in times, `LEAVE` attendance status, auto-generating logs on leave approval, and report updates.
- [x] **Phase 6: Faculty "My Attendance" History** - "My Attendance" screen with status summaries and date-wise detailed records.
- [x] **Phase 7: In-App Notifications** - Navbar notification badge, read/unread states, and notification list interface.
- [x] **Phase 8: Holiday & Non-working Day Integration** - Respecting configured school holidays and schedules during leave duration calculations.
- [x] **Phase 9: Security Hardening, Polish, and End-to-End Testing** - Enforcing RBAC permissions, multi-tenant isolation tests, UI polish, and E2E verification.

---

## Phase Details

### Phase 1: V2 Foundation & Database Models
**Goal**: Initialize Django apps, define `LeaveAllocation`, `LeaveRequest`, and `InAppNotification` models, and write baseline unit tests.
**Success Criteria**:
  1. `leaves` and `notifications` apps registered.
  2. Migrations run successfully, generating Postgres tables.
  3. Model unit tests verify database constraints, tenant scoping, and relationships.
**Plans**:
- [x] 01-01: Create `leaves` and `notifications` apps and register them in settings.
- [x] 01-02: Implement `LeaveAllocation`, `LeaveRequest`, and `InAppNotification` models inheriting from `TenantModel`. Run migrations.
- [x] 01-03: Write unit tests verifying tenant-scoped queries and model constraints.

### Phase 2: Excel Leave Allocation
**Goal**: Implement bulk Excel import for leave allocations with validation and feedback.
**Success Criteria**:
  1. Admin can download a sample Excel template.
  2. Excel upload validates columns, existing faculty, positive integers, and school ownership.
  3. Shows clear row-by-row success/failure report.
**Plans**:
- [x] 02-01: Implement Excel parser with `openpyxl` and validation checks.
- [x] 02-02: Create Admin Leave Allocation page with upload forms, validation preview, and errors.
- [x] 02-03: Write integration tests for bulk upload under multi-tenant constraints.

### Phase 3: Faculty Dashboard, Login & Leave Requests
**Goal**: Enable Faculty dashboard logins and the leave application flow.
**Success Criteria**:
  1. Faculty users can log in using standard authentication and access their dashboard.
  2. Faculty can view their remaining/allocated leave balances.
  3. Apply Leave form validates dates and prevents overlaps.
**Plans**:
- [x] 03-01: Update User password handling to support Faculty login.
- [x] 03-02: Build Faculty personal dashboard layout template.
- [x] 03-03: Implement Apply Leave form with date, balance, and overlap validations.

### Phase 4: Admin Leave Review & Approval
**Goal**: Create School Admin review interface for leave requests.
**Success Criteria**:
  1. School Admin can list and filter leave requests for their school.
  2. Admin can approve or reject (rejection requires a mandatory explanation).
**Plans**:
- [x] 04-01: Build School Admin leave requests dashboard with filters.
- [x] 04-02: Implement Approve and Reject endpoints with reason validation.

### Phase 5: Leave-Attendance Integration
**Goal**: Link approved leaves directly with attendance records.
**Success Criteria**:
  1. Approved leave dates automatically generate `AttendanceLog` records with status `LEAVE`.
  2. Attendance log `check_in_time` is nullable for `LEAVE` records.
  3. School Admin dashboards and reports count leave days appropriately.
**Plans**:
- [x] 05-01: Make `check_in_time` nullable and add `LEAVE` to `AttendanceLog.Status` choices.
- [x] 05-02: Implement post-save handlers to generate `AttendanceLog` records on leave approval.
- [x] 05-03: Update reporting and dashboard KPIs to handle `LEAVE` status.

### Phase 6: Faculty "My Attendance" History
**Goal**: Create visual attendance history page for Faculty.
**Success Criteria**:
  1. Faculty can view summary stats of Present/Absent/Late/Half Day/Leave counts.
  2. Faculty can scroll through a paginated date-wise history of check-in/out logs.
**Plans**:
- [x] 06-01: Implement Faculty "My Attendance" view and summary metrics.
- [x] 06-02: Build chronological detail table with check-in/out times.

### Phase 7: In-App Notifications
**Goal**: Implement real-time user notification badges and listings.
**Success Criteria**:
  1. Faculty navbar displays unread badge count.
  2. Triggers auto-generate notifications on submission, approval, and rejection.
**Plans**:
- [x] 07-01: Build context processor for notification count and notification list page.
- [x] 07-02: Add notification trigger hooks on leave actions.

### Phase 8: Holiday & Non-working Day Integration
**Goal**: Exclude holidays and non-working days from leave deduction counts.
**Success Criteria**:
  1. Leaves spanning holidays or weekends do not deduct balance for those days.
  2. Leave request validation accurately calculates net leave days.
**Plans**:
- [x] 08-01: Integrate schedule and holiday models into leave duration calculations.
- [x] 08-02: Write unit tests covering holiday leave exclusions.

### Phase 9: Security Hardening, Polish, and End-to-End Testing
**Goal**: Verify all permissions, tenant scoping, design matching, and E2E flows.
**Success Criteria**:
  1. Multi-tenant boundary tests pass (no cross-school data leaks).
  2. All user roles (Super Admin, School Admin, Faculty) restricted to their boundaries.
  3. UI styled to match Apple Design System specifications.
**Plans**:
- [x] 09-01: Secure V2 URL paths, prevent IDOR, and log auditable leave events.
- [x] 09-02: UI polish and final end-to-end integration tests.

---
*Roadmap updated: 2026-08-16*
