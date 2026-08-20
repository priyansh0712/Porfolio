# Phase 2: Student Master Records, Scoped CRUD & Student Portal - Context

## Overview
Phase 2 implements Student Master Records, Role-Based Scoped Access (School Admin Full CRUD vs Class Teacher Scoped CRUD with locked GR numbers), Student Transfer Request Workflow, and the View-only Student Login Portal.

## User Decisions & Key Specifications

### 1. Student Identification & GR Number
- **GR Number Entry:** Manual entry (matching the school's physical GR register e.g., `10452` or `GR-2026-001`).
- **Uniqueness:** Unique per school tenant (`UniqueConstraint(fields=['school', 'gr_number'])`).
- **Class Teacher Permission:**
  - Class Teacher **CAN enter** the initial GR Number when adding a new student to their own class.
  - Once created, the GR Number is **strictly locked (read-only)** for the Class Teacher; only School Admin can edit/modify an existing student's GR Number.
- **Roll Number:** Configured per Standard/Division for sorting and identification.

### 2. Student Fields (No Photo Required)
- **Basic Info:** Full Name, Date of Birth, Gender, Blood Group, Admission Date.
- **Parent/Guardian Info:** Guardian Name, Guardian Phone/Mobile, Emergency Contact, Residential Address.
- **Academic Placement:** Foreign Key to `Standard` and `Division`, plus active `AcademicYear` tracking.
- **Status & Soft-Delete:** `is_active=True` by default; soft-delete mechanism sets `is_active=False` to maintain data integrity.
- **Photo:** Not required — simple initial avatars (`initials`) used in UI.

### 3. Scoped Permissions & Role Matrix
- **School Admin:** Full CRUD across all standards and divisions, ability to edit GR numbers, activate/deactivate students, and approve/reject transfer requests.
- **Class Teacher:** Scoped CRUD strictly for students in their assigned division (resolved via `ClassTeacherAllocation`). GR number is disabled/read-only on create and edit.
- **Super Admin & Other Faculty:** No access to student data.

### 4. Student Class Transfer Workflow
- **Class Teacher Action:** Class Teacher can initiate a `StudentTransferRequest` for a student in their class, choosing the target Standard/Division and providing a reason.
- **School Admin Action:** Dedicated "Transfer Requests" view with 1-click **Approve** (automatically updates student's standard/division) or **Reject**.

### 5. Student Portal & Authentication
- **User Role:** Add `Role.STUDENT` to `apps.accounts.models.User`.
- **Credentials:** Student logs in using **GR Number** and default password **`Admin@123`**.
- **Student Dashboard:** View-only portal showing:
  - Personal details & enrollment info.
  - Assigned Class Teacher contact info.
  - Current enrolled subjects and respective subject teachers.
- **Security:** Students have no access to admin, faculty, or other student records.

### 6. Apple Design System UI
- Student Management Hub with:
  - Search by GR No / Name / Roll No.
  - Filters by Standard, Division, and Active/Inactive status.
  - Clean Apple modal sheets for Add Student, Edit Student, and Request Transfer.
  - Modern Apple styled status pills and badges.
