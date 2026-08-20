---
status: complete
phase: 02-student-master-records-scoped-crud-student-portal
source:
  - .planning/phases/02-student-master-records-scoped-crud-student-portal/02-01-PLAN.md
  - .planning/phases/02-student-master-records-scoped-crud-student-portal/02-02-PLAN.md
started: "2026-08-20T19:36:00.000Z"
updated: "2026-08-20T22:49:00.000Z"
---

## Tests

### 1. Cold Start Smoke Test
expected: Django dev server runs on http://greenwood.localhost:8000 without errors. Accessing the site returns live pages.
result: pass

### 2. Student Hub (Admin View)
expected: Log in as School Admin on http://greenwood.localhost:8000/login/. Click 'Students' in the top navbar to open http://greenwood.localhost:8000/students/. You see the Apple-styled Student Management hub with 'Students' and 'Transfers' tabs, search bar, Standard/Division filters, and student roster table.
result: pass

### 3. Add Student (School Admin)
expected: On http://greenwood.localhost:8000/students/, click '+ Add Student'. A clean Apple-style modal opens allowing selection of any Standard and Division, full name, gender, DOB, and GR Number. Submitting adds the student to the roster with initial avatars.
result: pass

### 4. Class Teacher Scoped View
expected: Log in as a Faculty user assigned as a Class Teacher. Click 'My Class' in navbar (or open /students/). The roster strictly displays only students from their assigned division. Standard & Division filter dropdowns are restricted.
result: pass

### 5. Class Teacher Edit Student (Locked GR Number)
expected: As a Class Teacher, click the Edit icon on a student in your class. The Edit modal opens with the GR Number field locked (grayed out/read-only). Editing full name or guardian phone and saving updates the student without modifying the GR Number.
result: pass

### 6. Transfer Request Workflow (Class Teacher)
expected: As a Class Teacher, click the Transfer icon on a student. Select a destination Standard & Division, optionally add a reason, and submit. The transfer appears under the 'Transfers' tab in 'Pending' status.
result: pass

### 7. Transfer Approval by School Admin
expected: Log in as School Admin, navigate to /students/?tab=transfers. You see the pending transfer request. Clicking 'Approve' atomically updates the student's assigned Standard & Division.
result: pass

### 8. Student Portal Login (GR Number + Admin@123)
expected: Log in on http://greenwood.localhost:8000/login/ using the student's GR Number and password 'Admin@123'. You are routed to http://greenwood.localhost:8000/students/portal/ showing a read-only profile banner, Class Teacher card, and assigned Subjects grid.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
