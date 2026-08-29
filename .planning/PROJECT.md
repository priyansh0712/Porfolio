# School Faculty Face Attendance SaaS & Academic Management (StudentERP1 V4)

## What This Is

A production-minded, multi-tenant SaaS platform for schools centered on webcam-based face recognition for faculty check-in/out attendance, leave management, full academic structure configuration (Academic Years, Standards, Divisions, Subjects, Class & Subject Teacher allocations), 4-step bulk Excel/CSV onboarding wizard for quick school setup, student records management with role-based CRUD permissions, dedicated Student Portal logins, Student Attendance engine, Subject Notes Upload & Class Teacher Approval pipeline, School Announcements, and Class Timetable system. Built with Django, PostgreSQL, Tailwind CSS, and Vanilla JavaScript adhering to the Apple Design System (`DESIGN-apple.md`).

## Core Value

Allow schools to effortlessly onboard and manage academic structures, teachers, subject allocations, student records, student attendance, study notes approval workflow, school announcements, and weekly class timetables with strict multi-tenant isolation (`school.ourapp.com`) and role-based permissions.

## Milestone Status: v4.0 Student Portal Features & Academic Content (COMPLETED)

**Goal:** Enhance the existing Student Portal and Academic workflows with Class Teacher student attendance marking & student history view, Subject Faculty notes upload with file type/size validation, Class Teacher note approval/rejection workflow, Approved Notes download portal for students, School Announcements, Class Timetable configuration & student view, and Student Portal Dashboard cards.

---

### Validated Milestones

- **v1.0 Face Recognition Attendance Platform**: Shipped 2026-08-15 (121 tests passing).
- **v2.0 Leave Management & Faculty Dashboard**: Shipped 2026-08-16 (159 tests passing).
- **v3.0 Academic Structure & Bulk Excel Onboarding**: Shipped 2026-08-21 (246 tests passing).
- **v4.0 Student Portal Features & Academic Content**: Shipped 2026-08-25 (45 tests passing).

---

## Context

- **Tech Stack**: Python 3.12, Django 5.1 backend, PostgreSQL 16 database, Tailwind CSS 3.4, Vanilla JavaScript, Apple Design System (`DESIGN-apple.md`).
- **Architecture**: Modular Django monolith (`tenants`, `accounts`, `faculty`, `biometrics`, `attendance`, `schedules`, `reports`, `leaves`, `notifications`, `academics`, `students`, `onboarding`, `notes`, `announcements`).
