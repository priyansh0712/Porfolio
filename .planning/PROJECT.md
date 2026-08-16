# School Faculty Face Attendance SaaS & Leave Management (StudentERP1 V2)

## What This Is

A production-minded, multi-tenant SaaS platform for schools centered on webcam-based face recognition for faculty check-in and check-out attendance, extended with faculty self-service leave management, personal attendance history dashboards, and real-time in-app notifications. Built with Django, PostgreSQL, Tailwind CSS, and Vanilla JavaScript, it offers isolated tenant environments (`school.ourapp.com`), configurable working schedules and late rules, audit logging for attendance integrity, and authorized school admin & faculty dashboards.

## Core Value

Allow school faculty to mark accurate check-in and check-out attendance using face recognition through a webcam with strict multi-tenant isolation, while giving authorized school administrators complete attendance management, rule configuration, leave reviews, and reporting, alongside faculty personal dashboards.

### Requirements

### Validated

- **V1 Core Platform**: All V1 requirements (TENANT-01, TENANT-02, LANDING-01, REG-01, AUTH-01, AUTH-02, AUTH-03, FAC-01, FACE-01, FACE-02, ATT-01, ATT-02, ATT-03, SCHED-01, SCHED-02, AUDIT-01, RPT-01, SEC-01) are fully validated and verified.
- **V2 Leave & Faculty Dashboard**: All V2 requirements (LEAVE-ALLOC, LEAVE-BAL, FAC-DASH, MY-ATT, LEAVE-REQ, LEAVE-APP, LEAVE-INT, LEAVE-NOTIF, LEAVE-OVERLAP, LEAVE-HOL, SEC-V2) are fully validated and verified (159 tests passing).

### Current State
- **V1.0 Milestone**: Complete & archived (2026-08-15).
- **V2.0 Milestone**: Complete & archived (2026-08-16).
- **Next Milestone**: Ready for V3.0 definition via `/gsd-new-milestone`.

### Active

*No active requirements. Initialize next milestone using `/gsd-new-milestone`.*

### Out of Scope

- [ ] **Student Attendance** — Deferred to future milestone to keep SaaS focused exclusively on faculty.
- [ ] **Student Management** — Deferred to future school management module.
- [ ] **School Bus Tracking** — Deferred to future transport module.
- [ ] **Parent Notifications / Communication Portal** — Deferred to future communication module.
- [ ] **Fees & Tuition Management** — Deferred to future finance module.
- [ ] **Payroll & Payroll Integration** — Deferred to future HR module.
- [ ] **Learning Management System (LMS)** — Deferred to future academic module.
- [ ] **Exams & Grading** — Deferred to future academic module.
- [ ] **Chatbots / AI Assistants** — Unnecessary complexity for core biometric attendance product.
- [ ] **Native Mobile Applications (iOS/Android)** — Web application with responsive UI is the focus.
- [ ] **Permanent Raw Facial Photo Storage** — Only biometric embeddings/vectors stored to protect privacy.
- [ ] **WhatsApp/SMS/Email notifications** — Notifications are strictly in-app for V2.

## Context

- **Target Market**: K-12 and private schools seeking an accurate, proxy-proof faculty attendance system without expensive biometric hardware.
- **Tech Stack**: Python 3.12, Django 5.1 backend, PostgreSQL 16 database, Tailwind CSS 3.4, Vanilla JavaScript (MediaDevices camera API), Django HTML templates.
- **Architecture**: Modular Django monolith with clean app boundaries (`tenants`, `accounts`, `faculty`, `biometrics`, `attendance`, `schedules`, `reports`, `leaves`, `notifications`).

## Constraints

- **Tech Stack**: Django templates + Tailwind CSS + Vanilla JS — NO React/Vue/Angular SPA frameworks.
- **Database**: PostgreSQL with strict multi-tenant isolation.
- **Hardware**: Standard webcam devices (built-in laptop webcams during development).
- **Multi-Tenancy**: Subdomain-based tenant resolution; isolation enforced at data-access layer.
- **Privacy & Roles**: Platform Super Admin must NOT have access to individual faculty records or face biometric data.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Django Monolith + Tailwind + Vanilla JS | Server-rendered templates eliminate SPA overhead while maintaining fast, responsive UX and high security | Verified |
| Multi-tenant Subdomain Routing | Provides isolated identity and clean data separation (`school.ourapp.com`) | Verified |
| Biometric Embeddings over Raw Images | Protects privacy, minimizes data footprint, and avoids compliance liability | Verified |
| Super Admin Data Access Restriction | Ensures customer trust by preventing platform admins from viewing faculty attendance/biometric records | Verified |
| Transactional Leave-Attendance Sync | Approved leave requests automatically generate status `LEAVE` logs in `AttendanceLog` | Verified |
| Holiday Exclusion Engine | Respects custom holidays and working schedules when calculating leave day subtractions | Verified |

---
*Updated: 2026-08-16 upon V2.0 completion*
