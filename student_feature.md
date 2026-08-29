Act as a Senior Product Architect, Senior Django Engineer, Senior SaaS Multi-Tenant Architect, Senior GSD Engineer, and Senior Education-Platform Engineer.

We are working on an EXISTING school SaaS project.

The project already has existing functionality including school management, faculty management, attendance, leave, student portal, multi-tenancy, authentication, and other existing modules.

Implement ONLY the Student Portal features described in this brief.

DO NOT rebuild the project.
DO NOT create a new project.
DO NOT use /gsd-new-project.
DO NOT rewrite existing modules.
DO NOT redesign unrelated pages.
DO NOT modify unrelated functionality.

First inspect the existing codebase and understand the current student, faculty, class, subject, attendance, portal, authentication, and school/tenant architecture.

Then create a focused GSD implementation plan.

Do not start coding until the plan is clear.

==================================================
GOAL
==================================================

Enhance the EXISTING Student Portal with exactly these features:

1. Class Teacher → Student Attendance
2. Subject Faculty → Notes Upload
3. Class Teacher → Notes Approval
4. Approved Notes → Student Portal
5. School Announcements → Student Portal
6. Student Timetable → Student Portal

Nothing beyond these features should be implemented.

==================================================
1. STUDENT ATTENDANCE
==================================================

The CLASS TEACHER of a class should be able to take attendance for students of their assigned class.

Expected flow:

Class Teacher
→ Select Class
→ Select Date
→ View students
→ Mark attendance
→ Save

Attendance statuses should support the existing attendance architecture.

At minimum support:

- Present
- Absent
- Half Day

If the existing project already has additional attendance states, reuse them instead of creating duplicate states.

The class teacher must only be able to take attendance for the class/classes assigned to them.

A class teacher must NOT be able to take attendance for another teacher's class unless the existing authorization system explicitly allows it.

Attendance must be tenant-specific.

School A must never access School B students or attendance.

==================================================
2. STUDENT ATTENDANCE VIEW
==================================================

Students must be able to view their own attendance through the Student Portal.

Student should see:

- Present
- Absent
- Half Day
- Attendance percentage/summary if already supported by the architecture

Also provide a date-wise attendance history.

Example:

Date       Status
01 Aug     Present
02 Aug     Present
03 Aug     Absent
04 Aug     Half Day

Students MUST NOT be able to:

- Modify attendance
- Mark their own attendance
- View another student's attendance

==================================================
3. SUBJECT FACULTY — NOTES UPLOAD
==================================================

Any faculty teaching a subject for a class should be able to upload notes for that subject/class.

Expected flow:

Subject Faculty
→ Select Class
→ Select Subject
→ Upload Note
→ Add title
→ Optional description
→ Submit

The uploaded note should initially have:

PENDING / WAITING FOR APPROVAL

status.

Notes must be associated with:

- School
- Class
- Subject
- Faculty
- Upload date
- Title
- Description if applicable
- File/document

Reuse the existing faculty/class/subject architecture.

Do NOT create duplicate faculty, class, or subject models.

==================================================
4. NOTE FILE UPLOAD
==================================================

Notes should support appropriate document formats based on the existing project.

At minimum evaluate support for:

- PDF
- DOC/DOCX
- PPT/PPTX
- Images where appropriate

Do not blindly allow arbitrary file types.

Implement reasonable:

- File type validation
- File size validation
- Safe file handling
- Secure storage
- Safe filenames

Reuse the existing media/file storage architecture if available.

Keep the implementation cloud-compatible.

==================================================
5. CLASS TEACHER — NOTE APPROVAL
==================================================

Uploaded notes must NOT immediately appear to students.

The workflow must be:

Subject Faculty
→ Upload Note
→ PENDING
→ Class Teacher reviews
→ APPROVE / REJECT

Only APPROVED notes should become visible to students.

Class Teacher should be able to:

- View pending notes for their assigned class
- Open/view note details
- Approve
- Reject
- Provide rejection reason

If rejected:

The note must NOT appear in the Student Portal.

The faculty who uploaded the note should be able to see the status.

Statuses should clearly distinguish:

- Pending
- Approved
- Rejected

==================================================
6. APPROVED NOTES — STUDENT PORTAL
==================================================

Students should see approved notes relevant to THEIR class.

Student should be able to filter/view notes by:

- Subject
- Date
- Faculty if useful

Example:

Mathematics
→ Algebra Notes
→ Uploaded by Rahul Sir
→ 20 Aug
→ View / Download

Physics
→ Chapter 3 Notes
→ Uploaded by Neha Ma'am
→ 21 Aug
→ View / Download

Students must ONLY see:

- Their own school
- Their own class
- Approved notes

Students must NOT see:

- Pending notes
- Rejected notes
- Notes from another class
- Notes from another school

==================================================
7. SCHOOL ANNOUNCEMENTS
==================================================

School should be able to publish announcements that appear in the Student Portal.

Use the EXISTING school/admin architecture.

If an appropriate School Admin role already exists, allow authorized school staff/admin to create announcements.

Announcement should support:

- Title
- Message/content
- Date/time
- Optional attachment if the existing architecture makes this simple
- Active/published status

Student Portal should show relevant announcements.

Example:

"Unit Test 2 will start from Monday."

"School will remain closed on Saturday."

Students should be able to view:

- Latest announcements
- Announcement details
- Date/time

Do NOT build a complex notification platform.

This feature is specifically for school announcements visible inside the Student Portal.

==================================================
8. TIMETABLE
==================================================

Students should be able to view their class timetable in the Student Portal.

Timetable should be associated with:

- School
- Class
- Day
- Period
- Subject
- Faculty
- Start time
- End time

Example:

Monday

08:00 - 08:45
Mathematics
Rahul Sir

08:45 - 09:30
Science
Neha Ma'am

09:45 - 10:30
English
Amit Sir

Students should only see the timetable for their own class.

Do NOT build teacher timetable management beyond what is required to display/manage the student class timetable.

If timetable management already exists in the project, reuse it.

If not, create the minimum admin functionality required to configure the class timetable.

==================================================
9. STUDENT PORTAL DASHBOARD
==================================================

Enhance the EXISTING Student Portal dashboard.

Add appropriate sections/cards for:

- Today's Attendance / Attendance Summary
- Latest Notes
- Latest Announcements
- Today's Timetable

Do NOT redesign the entire Student Portal.

Use the existing design system and layout.

Only add the requested functionality.

==================================================
10. ROLES & PERMISSIONS
==================================================

STUDENT:

Can:
- View own attendance
- View approved notes for own class
- View school announcements relevant to them
- View own class timetable

Cannot:
- Modify attendance
- Upload notes
- Approve/reject notes
- Modify announcements
- Modify timetable
- View another student's private data

CLASS TEACHER:

Can:
- Take attendance for assigned class
- View assigned class attendance
- Review notes uploaded for assigned class
- Approve/reject notes for assigned class

Cannot:
- Access another school's data
- Take attendance for unrelated classes unless explicitly authorized by the existing system

SUBJECT FACULTY:

Can:
- Upload notes for classes/subjects they actually teach

Cannot:
- Approve their own notes unless the existing role/assignment architecture explicitly requires it
- Upload notes to unrelated classes
- Access another school's data

SCHOOL ADMIN:

Can manage the school-level functionality required for:
- Announcements
- Timetable
- Class/faculty/student assignments where the existing system already supports management

SUPER ADMIN:

Do not give Super Admin unnecessary access to student operational data.

Preserve the existing Super Admin privacy model.

==================================================
11. MULTI-TENANCY
==================================================

This is NON-NEGOTIABLE.

Every feature must respect the existing school/tenant isolation.

School A:

Students
Classes
Attendance
Notes
Announcements
Timetable

must never be accessible from School B.

Do not rely only on hiding UI.

Backend authorization and tenant filtering must enforce this.

Test cross-tenant access explicitly.

==================================================
12. CLASS / SUBJECT RELATIONSHIPS
==================================================

Before implementing anything, inspect the existing architecture for:

- School
- Student
- Faculty
- Class
- Subject
- Class Teacher assignment
- Faculty Subject assignment

Reuse existing relationships.

Do NOT create duplicate versions of these models.

The system should understand:

Class
→ Class Teacher

Class
→ Students

Class
→ Subjects

Subject
→ Faculty

Faculty
→ Subject/Class assignment

Use these existing relationships for authorization.

==================================================
13. NOTE APPROVAL SECURITY
==================================================

A subject faculty must not be able to approve their own note unless explicitly allowed by the existing business rules.

The Class Teacher approval must be verified server-side.

A user must not be able to change:

- class ID
- school ID
- note ID
- subject ID

in a request to bypass authorization.

==================================================
14. ATTENDANCE SECURITY
==================================================

Class Teacher attendance must be validated server-side.

A teacher cannot submit attendance for a class they are not assigned to.

Students cannot submit or modify attendance.

Attendance must remain linked to:

- Student
- Class
- School
- Date

Use the existing attendance model if appropriate.

Do not create a second unrelated attendance system.

==================================================
15. NOTIFICATIONS
==================================================

Do not build a new notification infrastructure unless the existing project already has one.

If existing in-app notifications exist, reuse them where appropriate.

Useful notification cases may include:

- Note approved
- Note rejected
- New school announcement

But keep notification behavior limited to what the existing system can support cleanly.

==================================================
16. UI / UX
==================================================

Continue using the existing technology stack.

Do NOT introduce:

- React
- Vue
- Angular
- New frontend frameworks

Use the existing:

- Django Templates
- Tailwind CSS
- Vanilla JavaScript where necessary

Do not redesign existing pages.

Add only the required:

- Attendance section
- Notes section
- Announcements section
- Timetable section

Keep the UI consistent with the existing Student Portal.

==================================================
17. TESTING
==================================================

Add focused tests for:

ATTENDANCE:
- Class teacher can take assigned class attendance
- Class teacher cannot take unrelated class attendance
- Student can view own attendance
- Student cannot modify attendance
- Student cannot view another student's attendance

NOTES:
- Subject faculty can upload notes for assigned subject/class
- Faculty cannot upload notes to unrelated class
- Uploaded notes start as Pending
- Class teacher can approve
- Class teacher can reject
- Rejection reason works
- Approved notes appear to correct students
- Pending notes do not appear
- Rejected notes do not appear
- Student cannot access notes from another class
- Student cannot access notes from another school

ANNOUNCEMENTS:
- Authorized school user can create announcement
- Students see relevant announcements
- Unauthorized users cannot modify announcements

TIMETABLE:
- Student sees own class timetable
- Student cannot access another class timetable
- Timetable is tenant-isolated

MULTI-TENANCY:
- School A cannot access School B data
- IDs cannot be manipulated to bypass tenant isolation

REGRESSION:
- Existing V1/V2 functionality still works.

==================================================
18. STRICT SCOPE
==================================================

ONLY implement these six capabilities:

1. Class Teacher Student Attendance
2. Subject Faculty Notes Upload
3. Class Teacher Notes Approval
4. Approved Notes in Student Portal
5. School Announcements in Student Portal
6. Student Timetable

DO NOT implement:

- Parent portal
- Bus tracking
- Fees
- Payroll
- Exams
- Homework management
- Chat system
- Messaging platform
- LMS
- New mobile app
- AI chatbot
- Unrelated analytics
- Unrelated redesign
- Any other feature

If you discover unrelated bugs or improvement opportunities:

DO NOT fix them.

Report them only.

==================================================
19. GSD WORKFLOW
==================================================

This is an EXISTING project.

Do NOT use /gsd-new-project.

First inspect the existing codebase and understand:

- Student Portal
- Student model
- Faculty model
- Class model
- Subject model
- Class Teacher relationship
- Faculty Subject/Class assignment
- Existing attendance
- Existing file/media handling
- Existing notifications
- Existing school/tenant architecture
- Existing permissions
- Existing timetable functionality if any

Then create a focused GSD plan.

Do not immediately modify unrelated code.

Break the work into logical phases based on actual dependencies.

Suggested high-level order:

Phase 1:
Student attendance for class teachers

Phase 2:
Notes upload + approval workflow

Phase 3:
Approved notes in Student Portal

Phase 4:
School announcements

Phase 5:
Class timetable + Student Portal timetable

Phase 6:
Student dashboard integration + testing/security

You may change the phase order if inspection shows a better dependency order.

After each phase:

- Run tests
- Verify permissions
- Verify tenant isolation
- Verify existing functionality
- Check for regressions

==================================================
20. FINAL RULE
==================================================

The existing project is already working.

Treat all existing functionality as protected.

Do not rebuild it.

Do not redesign it.

Do not refactor unrelated code.

Make the smallest clean changes required to add ONLY the requested Student Portal functionality.

First inspect the existing architecture.

Then create the GSD plan.

Then implement.

Then test.

Do not start coding blindly.