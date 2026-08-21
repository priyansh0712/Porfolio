# Phase 4 Context — Faculty & Student Views, Password Security & Integration Polish

## Phase Objective
Deliver dedicated teacher dashboards ("My Class" & "My Subjects"), self-service password management for Faculty and Students, and comprehensive multi-tenant security verification.

---

## Technical Decisions & Architecture

### 1. Faculty Dashboards (`apps/faculty/views.py`)
- **"My Class" (`/faculty/my-class/`)**:
  - Resolves active `ClassTeacherAllocation` for `request.user.faculty_profile` in the active `AcademicYear`.
  - Displays assigned Division details, student roster (roll number, GR number, full name, gender, guardian phone, status).
  - Provides quick action button "+ Add Student" opening a modal pre-filled with the teacher's assigned Standard and Division, with GR Number input enabled (for new student additions).
  - Displays a banner if the faculty member is not currently assigned as a Class Teacher for the active academic year.

- **"My Subjects" (`/faculty/my-subjects/`)**:
  - Queries `SubjectTeacherAllocation` for `request.user.faculty_profile` in the active `AcademicYear`.
  - Groups allocations by Subject and Class Division.
  - Displays read-only student rosters for each taught subject and division with roll numbers, names, and guardian contact numbers.

### 2. Self-Service Password & Profile Management (`apps/accounts/views.py` & `apps/students/views.py`)
- **Shared Password Change View (`/accounts/password/change/`)**:
  - Accessible to logged-in users of all roles (School Admin, Faculty, Student).
  - Standard Django `PasswordChangeForm` requiring old password verification + new password validation (min 8 chars, mixed case, numbers).
  - On successful update, keeps user logged in via `update_session_auth_hash`.
  - Apple Design System styled layout with success alert banner.

### 3. Multi-Tenant & Role Security Polish (`apps/accounts/permissions.py`)
- **Permissions Audit**:
  - Ensure all views inherit tenant scoping (`school=request.tenant`).
  - `ClassTeacherRequiredMixin`: Ensures user is an active Faculty member assigned as Class Teacher.
  - `StudentRequiredMixin`: Ensures user role is `STUDENT` and scopes profile queries to `user=request.user`.

---

## Deliverables Checklist

- [ ] `apps/faculty/views.py` — `MyClassView` and `MySubjectsView`.
- [ ] `apps/faculty/urls.py` — Register `/faculty/my-class/` and `/faculty/my-subjects/`.
- [ ] `templates/faculty/my_class.html` — Apple Design System Class Teacher dashboard with "+ Add Student" modal.
- [ ] `templates/faculty/my_subjects.html` — Apple Design System Subject Teacher dashboard.
- [ ] `templates/components/navbar_faculty.html` — Update navigation links to include "My Class" and "My Subjects".
- [ ] `apps/accounts/views.py` — `SelfPasswordChangeView`.
- [ ] `templates/accounts/password_change.html` — Password update form.
- [ ] `apps/faculty/tests.py` & `apps/accounts/tests.py` — Unit test suite verifying teacher dashboards, password changes, and multi-tenant security boundaries.
