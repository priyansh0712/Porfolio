Act as a Senior Product Architect, Senior Django Engineer, Senior SaaS Architect, Senior Database Architect, Senior Security Engineer, and Senior GSD Engineer.

We already have a completed and working V1 of our school faculty attendance SaaS platform.

DO NOT rebuild V1.
DO NOT create a new project.
DO NOT replace the existing architecture.
DO NOT break existing V1 functionality.

Your job is to inspect the existing codebase first, understand the current architecture, models, authentication, multi-tenancy, attendance system, UI structure, and existing tests, and then plan and implement V2 as an extension of the existing product using the GSD workflow.

==================================================
V2 PRODUCT SCOPE
==================================================

V2 has TWO connected goals:

1. Faculty Leave Management
2. Faculty Personal Attendance Dashboard

The existing V1 face-based attendance system must remain fully functional.

V2 must integrate with the existing attendance system instead of creating a second independent attendance system.

==================================================
FEATURE 1 — ADMIN EXCEL LEAVE ALLOCATION
==================================================

School Admin must be able to upload an Excel file containing how much leave each faculty member is allocated.

Example:

Faculty ID | Faculty Name | Casual Leave | Sick Leave | Paid Leave
F001       | Rahul Patel  | 12           | 10         | 15
F002       | Neha Shah   | 10           | 12         | 15

IMPORTANT:

The Excel file is NOT for creating faculty.

Faculty must already exist in the system.

The Excel upload is only for assigning/updating leave allocation for existing faculty.

The system must:

- Accept Excel upload
- Validate file type
- Validate required columns
- Validate faculty identifiers
- Ensure faculty belongs to the current school
- Detect duplicate rows
- Validate numeric leave values
- Reject invalid negative values
- Show row-level validation errors
- Process valid rows safely
- Never modify another school's faculty
- Show upload summary
- Preserve data integrity

Example result:

48 rows processed
45 successful
3 failed

The admin should be able to understand exactly why failed rows were rejected.

Do not silently ignore invalid rows.

==================================================
FEATURE 2 — FACULTY LEAVE BALANCE
==================================================

Each faculty member should have leave allocation.

For each leave type track:

- Allocated
- Used
- Remaining

Example:

Casual Leave
Allocated: 12
Used: 3
Remaining: 9

Pending leave requests must NOT reduce the used balance.

Only approved leave should reduce the available balance.

Rejected leave must not reduce the balance.

Cancelled leave must restore the appropriate balance if applicable.

Design this using the existing database architecture rather than creating unnecessary duplicated data.

==================================================
FEATURE 3 — FACULTY LOGIN / DASHBOARD
==================================================

Faculty must have access to a personal dashboard.

Faculty must only be able to access their own information.

Faculty dashboard should include:

- Today's attendance
- Attendance summary
- Attendance history
- Leave balance
- Leave requests
- Notifications

Faculty MUST NOT be able to:

- View another faculty's attendance
- View another faculty's leave
- Modify attendance
- Approve/reject leave
- Access School Admin functionality
- Access another school's data

==================================================
FEATURE 4 — MY ATTENDANCE
==================================================

Faculty should be able to view their own attendance.

At minimum support:

- Present
- Absent
- Half Day
- Late
- Leave
- Holiday / Non-working day where applicable

Show summary such as:

Present: 18
Absent: 2
Half Day: 1
Late: 3
Leave: 3

Also provide date-wise records:

Date
Status
Check-in
Check-out
Working duration where available

Use the existing V1 attendance records.

DO NOT create a second attendance table/system unless the existing architecture genuinely requires an extension.

==================================================
FEATURE 5 — APPLY LEAVE
==================================================

Faculty can apply for leave.

Form:

- Leave Type
- From Date
- To Date
- Reason

System must validate:

- Faculty is authenticated
- Faculty belongs to current school
- Leave type is valid
- Dates are valid
- From date is not after To date
- Leave does not overlap an existing approved/pending conflicting request
- Leave balance is sufficient where the leave type requires balance
- Non-working days/holidays are handled according to school policy
- Duplicate/conflicting requests are prevented

New requests start as:

PENDING

==================================================
FEATURE 6 — ADMIN LEAVE APPROVAL
==================================================

School Admin can view leave requests for ONLY their school.

Admin can:

- View pending requests
- View request details
- Approve
- Reject
- Provide rejection reason
- View leave history
- Filter by faculty
- Filter by date
- Filter by status
- Filter by leave type

Rejecting a leave request should require a reason.

==================================================
FEATURE 7 — LEAVE → ATTENDANCE INTEGRATION
==================================================

This is a CRITICAL requirement.

Approved leave must automatically integrate with the existing attendance system.

Example:

Faculty:
20 Aug → Approved Leave
21 Aug → Approved Leave
22 Aug → Approved Leave

Those dates must appear as:

LEAVE

They must NOT appear as:

ABSENT

The system must ensure that approved leave is reflected consistently across:

- Faculty dashboard
- Admin attendance dashboard
- Attendance history
- Attendance reports
- Attendance calculations

Do NOT duplicate attendance records unnecessarily.

Define clearly whether leave is represented as an attendance state, derived status, or another appropriate domain model.

Choose the approach that best fits the existing V1 architecture.

==================================================
FEATURE 8 — LEAVE NOTIFICATIONS
==================================================

When faculty submits a leave request:

Faculty should see:

PENDING

When School Admin approves:

Faculty receives an in-app notification.

Example:

"Your leave request for 20 Aug - 22 Aug has been approved."

When rejected:

"Your leave request for 20 Aug - 22 Aug has been rejected."

Rejection reason should be available.

V2 should initially use IN-APP NOTIFICATIONS.

Do NOT add WhatsApp, SMS, email or push notification infrastructure unless the existing project already has it and it is trivial to integrate.

Those are future enhancements.

Notification should include:

- Title
- Message
- Created time
- Read/unread state
- Related leave request where useful

==================================================
FEATURE 9 — LEAVE OVERLAP RULES
==================================================

Prevent invalid overlapping requests.

Example:

Existing:
20 Aug - 22 Aug APPROVED

New:
21 Aug - 23 Aug

This should be rejected or blocked with a clear message.

Also define behavior for:

PENDING + new request
APPROVED + new request
REJECTED + new request
CANCELLED + new request

Do not allow ambiguous duplicate leave requests.

==================================================
FEATURE 10 — HOLIDAY / NON-WORKING DAY INTEGRATION
==================================================

The V1 system already has configurable working days/schedules.

V2 must respect those rules.

Do not blindly count every calendar day as leave.

For example:

If Saturday is a non-working day:

Friday → Leave
Saturday → Non-working day
Sunday → Holiday

The leave calculation must follow the school's configured policy.

If the existing V1 architecture does not support this cleanly, inspect it first and propose the smallest safe extension.

Do not duplicate schedule logic.

==================================================
MULTI-TENANCY
==================================================

This remains NON-NEGOTIABLE.

Every V2 feature must respect the existing tenant isolation.

School A:
- Faculty
- Leave allocations
- Leave requests
- Notifications
- Attendance

must never be accessible from School B.

Test cross-tenant access explicitly.

Do not rely on frontend filtering.

All backend queries and permissions must enforce tenant ownership.

==================================================
ROLE PERMISSIONS
==================================================

SUPER ADMIN:

Can manage platform/school-level metadata according to V1.

Must NOT gain access to:
- Faculty attendance
- Faculty leave requests
- Faculty leave balances
- Faculty notifications
- Biometric data

SCHOOL ADMIN:

Can:
- Upload leave Excel
- Manage leave allocation
- View school faculty leave
- Approve/reject leave
- View school attendance
- View school reports

FACULTY:

Can:
- View own attendance
- Apply leave
- View own leave balance
- View own leave history
- View own notifications

Faculty cannot modify attendance.

==================================================
EXCEL UPLOAD UX
==================================================

Admin should have:

Leave Management
→ Leave Allocation
→ Upload Excel

Provide:
- Download sample/template Excel
- Upload
- Validation preview if appropriate
- Errors
- Success summary
- Failed rows report if useful

Do not make the admin guess the Excel format.

==================================================
DATABASE / ARCHITECTURE
==================================================

Before changing code:

INSPECT THE EXISTING CODEBASE.

Understand:
- Django apps
- Models
- Relationships
- Existing attendance models
- School/tenant model
- User/auth model
- Faculty model
- Existing schedule models
- Existing permissions
- Existing URLs/views/templates
- Existing Tailwind structure
- Existing tests

Then determine the minimum clean extension.

Avoid:
- Duplicate models
- Duplicate attendance logic
- Duplicate tenant logic
- Giant views
- Hardcoded school IDs
- Hardcoded leave values
- Business logic inside templates

Use PostgreSQL and existing Django architecture.

==================================================
UI / FRONTEND
==================================================

Continue using:

Django Templates
Tailwind CSS
Minimal Vanilla JavaScript

Do NOT introduce:
- React
- Vue
- Angular
- unnecessary frontend frameworks

The V2 UI must visually match the existing V1 design system.

Do not redesign the entire V1.

Add:
- Leave Management
- Leave Allocation
- Leave Requests
- Leave Balance
- My Attendance
- Notifications

Use clear states:

Pending
Approved
Rejected
Cancelled

==================================================
SECURITY
==================================================

Pay special attention to:

- Role-based permissions
- Tenant isolation
- IDOR prevention
- Excel upload validation
- File size limits
- Malicious Excel/file handling
- CSRF
- Authentication
- Authorization
- Sensitive data exposure
- Audit logging

A faculty must not be able to change a URL/ID and access another faculty's leave or attendance.

A School Admin must not access another school's leave data.

Super Admin must not gain normal access to school operational data.

==================================================
AUDIT LOGGING
==================================================

Important leave actions should be auditable.

Track where appropriate:

- Leave submitted
- Leave approved
- Leave rejected
- Leave cancelled
- Leave allocation uploaded/changed
- Who performed the action
- Timestamp
- Reason where relevant

Do not silently modify important leave data.

==================================================
TESTING
==================================================

Before declaring V2 complete, test:

AUTH:
- Faculty login
- Admin login
- Unauthorized access
- Role permissions

TENANCY:
- School A cannot access School B leave
- School A cannot access School B attendance
- School A cannot access School B notifications

EXCEL:
- Valid Excel
- Invalid file
- Missing columns
- Invalid faculty ID
- Faculty from another school
- Duplicate rows
- Negative leave values
- Non-numeric values
- Partial failure

LEAVE:
- Apply leave
- Approve
- Reject
- Rejection reason
- Balance deduction
- Rejected balance unchanged
- Pending balance unchanged
- Overlapping leave
- Invalid date range
- Insufficient balance
- Holiday/non-working day handling

ATTENDANCE:
- Present
- Absent
- Half Day
- Late
- Leave
- Check-in
- Check-out
- Approved leave reflected correctly

NOTIFICATIONS:
- Approval notification
- Rejection notification
- Read/unread state

PERMISSIONS:
- Faculty cannot modify attendance
- Faculty cannot approve leave
- Faculty cannot see another faculty's data
- Admin cannot access another school
- Super Admin cannot access faculty operational data

==================================================
GSD EXECUTION PROCESS
==================================================

Do NOT immediately start coding.

First inspect the existing V1.

Then:

1. Analyze existing architecture
2. Identify reusable V1 components
3. Identify required schema changes
4. Identify risks
5. Identify ambiguities
6. Research only where necessary
7. Create V2 requirements
8. Create V2 implementation plan
9. Break V2 into logical phases
10. Define acceptance criteria for each phase

Suggested phase structure:

Phase 1:
V2 foundation + database/domain models

Phase 2:
Excel leave allocation

Phase 3:
Faculty leave application + leave balance

Phase 4:
Admin approval/rejection

Phase 5:
Leave-attendance integration

Phase 6:
Faculty attendance dashboard

Phase 7:
Notifications

Phase 8:
Security, permissions, tenant isolation and audit testing

Phase 9:
UI polish + end-to-end testing

You may change this ordering if inspection shows a better dependency structure.

Do NOT blindly follow the suggested phases.

Each phase must:
- Have clear scope
- Have acceptance criteria
- Be independently testable
- Avoid breaking V1

After each implementation phase:
- Run tests
- Verify functionality
- Check regressions
- Check tenant isolation
- Check permissions
- Review code quality

==================================================
CRITICAL RULE
==================================================

V1 is already working.

Treat V1 as a protected baseline.

Before modifying existing code, understand how it works.

Do not rewrite working V1 modules just to make V2 code "cleaner".

Prefer small, backward-compatible extensions.

If an existing V1 implementation is technically weak but not blocking V2, do not rewrite it unnecessarily.

If you find a critical security or data-integrity issue in V1 that V2 depends on, stop and report it before proceeding.

==================================================
FINAL GOAL
==================================================

Build V2 as a clean extension of the existing SaaS:

V1:
Face-based Faculty Attendance

+

V2:
Faculty Leave Management
+
Personal Attendance Dashboard
+
Leave Notifications

Final faculty experience:

Faculty Login
→ Dashboard
→ Today's Attendance
→ My Attendance
→ Leave Balance
→ Apply Leave
→ Leave History
→ Notifications

Final admin experience:

Admin Login
→ Dashboard
→ Leave Management
→ Upload Leave Allocation Excel
→ Review Leave Requests
→ Approve / Reject
→ Attendance + Leave integrated reporting

Do not add student, bus, parent, payroll, WhatsApp or unrelated modules.

Start by inspecting the existing V1 codebase and producing the V2 plan before implementation.