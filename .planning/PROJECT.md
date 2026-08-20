# School Faculty Face Attendance SaaS & Academic Management (StudentERP1 V3)

## What This Is

A production-minded, multi-tenant SaaS platform for schools centered on webcam-based face recognition for faculty check-in/out attendance, leave management, full academic structure configuration (Academic Years, Standards, Divisions, Subjects, Class & Subject Teacher allocations), 4-step bulk Excel/CSV onboarding wizard for quick school setup, and student records management with role-based CRUD permissions. Built with Django, PostgreSQL, Tailwind CSS, and Vanilla JavaScript adhering to the Apple Design System (`DESIGN-apple.md`).

## Core Value

Allow schools to effortlessly onboard and manage academic structures, teachers, subject allocations, and student records via intuitive Excel/CSV bulk import wizards with strict validation, while providing isolated tenant environments (`school.ourapp.com`), secure role-based access for Principals and Class Teachers, and biometric face attendance for faculty.

## Current Milestone: v3.0 Academic Structure & Bulk Excel Onboarding

**Goal:** Build complete Academic Management, 4-step Excel/CSV bulk onboarding wizard (Teachers, Class Teachers, Subject Mappings, Students) with atomic validation previews, student record CRUD with role-based permissions (Principal full CRUD, Class Teacher scoped CRUD, soft-deletes, GR-number protection), and faculty self-service password management.

**Target features:**
- **Academic Hierarchy**: AcademicYear, Standard, Division, Subject, and Class/Subject Teacher allocation models with multi-tenant isolation.
- **Bulk Importer Wizard**: 4-step sequential Excel/CSV upload (`.xlsx` & `.csv`) with downloadable sample templates, data validation preview, and atomic rollback commit.
- **Auto-Account Creation**: Automatically generate faculty user accounts with default password `Admin@123` upon bulk teacher import.
- **Student Master & Scoped CRUD**: Student profiles with unique GR Number, roll number, contact details, soft delete (`is_active=False`), and Class Teacher transfer requests.
- **Role-Based Permissions**: Principal has full CRUD across school; Class Teacher has scoped CRUD on their assigned class with protected GR Numbers; Subject Teacher has read-only view.
- **Faculty Class & Subject Views**: Dedicated "My Class" and "My Subjects" dashboards in faculty portal.
- **Faculty Password Change**: Self-service credential update on first login.

### Requirements

### Validated

- **V1 Core Platform**: All V1 requirements (TENANT-01, TENANT-02, LANDING-01, REG-01, AUTH-01, AUTH-02, AUTH-03, FAC-01, FACE-01, FACE-02, ATT-01, ATT-02, ATT-03, SCHED-01, SCHED-02, AUDIT-01, RPT-01, SEC-01) are fully validated and verified (121 tests passing).
- **V2 Leave & Faculty Dashboard**: All V2 requirements (LEAVE-ALLOC, LEAVE-BAL, FAC-DASH, MY-ATT, LEAVE-REQ, LEAVE-APP, LEAVE-INT, LEAVE-NOTIF, LEAVE-OVERLAP, LEAVE-HOL, SEC-V2) are fully validated and verified (159 tests passing).

### Active (v3.0)

- [ ] **ACAD-01**: School Admin can create and manage Academic Years (with active session toggle), Standards (Grades), Divisions (Sections), and Subjects.
- [ ] **ALLOC-01**: School Admin can assign Class Teachers to Divisions (1-to-1) and Subject Teachers to Standard+Division+Subject combinations.
- [ ] **BULK-01**: School Admin can download structured sample Excel (`.xlsx`) and CSV templates for all 4 onboarding steps.
- [ ] **BULK-02**: Step 1 Faculty Bulk Import — upload teachers list with atomic validation preview and automatic user account creation (`Admin@123` default password).
- [ ] **BULK-03**: Step 2 & 3 Allocation Bulk Import — upload Class Teacher and Subject Teacher mappings with dependency validation against existing teachers and classes.
- [ ] **BULK-04**: Step 4 Student Bulk Import — upload students with unique GR No check, roll number validation, standard/division linking, and atomic commit.
- [ ] **STU-01**: Principal has full CRUD on student records (including GR Number edits and permanent/soft delete management).
- [ ] **STU-02**: Class Teacher has scoped CRUD for their assigned class students with locked/read-only GR Number and class transfer request action.
- [ ] **FAC-VIEW**: Faculty dashboard provides dedicated "My Class" (for Class Teachers) and "My Subjects" (for Subject Teachers) views.
- [ ] **AUTH-PASS**: Faculty can change their password and profile details upon login.

### Out of Scope

- [ ] **Student Attendance** — Deferred to future milestone (manual click/webcam attendance for students).
- [ ] **School Bus Tracking** — Deferred to future transport module.
- [ ] **Parent Notifications / Communication Portal** — Deferred to future communication module.
- [ ] **Fees & Tuition Management** — Deferred to future finance module.
- [ ] **Exams & Grading** — Deferred to future academic grading module.

## Context

- **Tech Stack**: Python 3.12, Django 5.1 backend, PostgreSQL 16 database, Tailwind CSS 3.4, Vanilla JavaScript, openpyxl, Apple Design System (`DESIGN-apple.md`).
- **Architecture**: Modular Django monolith (`tenants`, `accounts`, `faculty`, `biometrics`, `attendance`, `schedules`, `reports`, `leaves`, `notifications`, `academics`, `students`).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 4-Step Sequential Bulk Wizard | Enforces proper data dependency order (Teachers → Classes → Subjects → Students) preventing orphaned records | Pending v3.0 |
| Atomic Upload Preview & Validation | Prevents corrupted/partial imports; school admin sees exact row issues before committing to DB | Pending v3.0 |
| Scoped Class Teacher Permissions | Class teachers can manage their students but cannot tamper with other classes or official GR numbers | Pending v3.0 |
| Soft Delete for Students | Keeps historical audit logs, TC generation, and past academic records intact | Pending v3.0 |
| Support both .xlsx and .csv | Maximum convenience for school staff using Excel or third-party exports | Pending v3.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Updated: 2026-08-20 upon Milestone v3.0 Initialization*
