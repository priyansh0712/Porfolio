# School Faculty Face Attendance SaaS & Academic Management (StudentERP1 V3)

## What This Is

A production-minded, multi-tenant SaaS platform for schools centered on webcam-based face recognition for faculty check-in/out attendance, leave management, full academic structure configuration (Academic Years, Standards, Divisions, Subjects, Class & Subject Teacher allocations), 4-step bulk Excel/CSV onboarding wizard for quick school setup, student records management with role-based CRUD permissions, and dedicated Student Portal logins. Built with Django, PostgreSQL, Tailwind CSS, and Vanilla JavaScript adhering to the Apple Design System (`DESIGN-apple.md`).

## Core Value

Allow schools to effortlessly onboard and manage academic structures, teachers, subject allocations, and student records via intuitive Excel/CSV bulk import wizards with strict validation, while providing isolated tenant environments (`school.ourapp.com`), secure role-based access for Principals, Teachers, and Students (with GR Number login), and biometric face attendance for faculty.

## Current Milestone: v3.0 Academic Structure & Bulk Excel Onboarding (SHIPPED)

**Goal:** Build complete Academic Management, 4-step Excel/CSV bulk onboarding wizard (Teachers, Class Teachers, Subject Mappings, Students) with atomic validation previews, student record CRUD with role-based permissions (Principal full CRUD, Class Teacher scoped CRUD, soft-deletes, GR-number protection), Student Login Portal (Username = GR No, default password = `Admin@123`), and self-service password management.

**Delivered features:**
- **Academic Hierarchy**: AcademicYear, Standard, Division, Subject, and Class/Subject Teacher allocation models with multi-tenant isolation.
- **Bulk Importer Wizard**: 4-step sequential Excel/CSV upload (`.xlsx` & `.csv`) with downloadable sample templates, data validation preview, and atomic rollback commit.
- **Auto-Account Creation**: Automatically generate faculty user accounts and student user accounts (Username = GR Number) with default password `Admin@123`.
- **Student Master & Scoped CRUD**: Student profiles with unique GR Number, roll number, contact details, soft delete (`is_active=False`), and Class Teacher transfer requests.
- **Student Portal Login**: Students can log in using their GR Number + `Admin@123` to view their personal profile, assigned standard/division, class teacher, and subjects.
- **Role-Based Permissions**: Principal has full CRUD across school; Class Teacher has scoped CRUD on their assigned class with protected GR Numbers; Subject Teacher has read-only view; Student has read-only personal profile view.
- **Faculty Class & Subject Views**: Dedicated "My Class" and "My Subjects" dashboards in faculty portal.
- **Self-Service Password Change**: Faculty and Students can change their password and profile details upon login.

---

### Validated Milestones

- **v1.0 Core Platform**: All V1 requirements (TENANT-01 to TENANT-02, LANDING-01, REG-01, AUTH-01 to AUTH-03, FAC-01, FACE-01 to FACE-02, ATT-01 to ATT-03, SCHED-01 to SCHED-02, AUDIT-01, RPT-01, SEC-01) are fully validated and verified (121 tests passing).
- **v2.0 Leave Management**: All V2 requirements (LEAVE-ALLOC, LEAVE-BAL, FAC-DASH, MY-ATT, LEAVE-REQ, LEAVE-APP, LEAVE-INT, LEAVE-NOTIF, LEAVE-OVERLAP, LEAVE-HOL, SEC-V2) are fully validated and verified (159 tests passing).
- **v3.0 Academic Structure & Bulk Excel Onboarding**: All V3 requirements (`ACAD-01..04`, `ALLOC-01..03`, `STU-01..06`, `BULK-01..05`, `FAC-01..02`, `AUTH-01`, `SEC-01`) are fully validated and verified (246 tests passing).

---

## Context

- **Tech Stack**: Python 3.12, Django 5.1 backend, PostgreSQL 16 database, Tailwind CSS 3.4, Vanilla JavaScript, openpyxl, Apple Design System (`DESIGN-apple.md`).
- **Architecture**: Modular Django monolith (`tenants`, `accounts`, `faculty`, `biometrics`, `attendance`, `schedules`, `reports`, `leaves`, `notifications`, `academics`, `students`, `onboarding`).

---
*Updated: 2026-08-21 upon Milestone v3.0 completion*
