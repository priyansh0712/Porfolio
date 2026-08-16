# School Faculty Face Attendance SaaS (StudentERP1 V1)

## What This Is

A production-minded, multi-tenant SaaS platform for schools centered on webcam-based face recognition for faculty check-in and check-out attendance. Built with Django, PostgreSQL, Tailwind CSS, and Vanilla JavaScript, it offers isolated tenant environments (`school.ourapp.com`), configurable working schedules and late rules, audit logging for attendance integrity, and an authorized school admin dashboard, along with a public company landing page and school self-registration.

## Core Value

Allow school faculty to mark accurate check-in and check-out attendance using face recognition through a webcam with strict multi-tenant isolation, while giving authorized school administrators complete attendance management, rule configuration, and reporting.

### Requirements

### Validated

- **V1 Core Platform**: All V1 requirements (TENANT-01, TENANT-02, LANDING-01, REG-01, AUTH-01, AUTH-02, AUTH-03, FAC-01, FACE-01, FACE-02, ATT-01, ATT-02, ATT-03, SCHED-01, SCHED-02, AUDIT-01, RPT-01, SEC-01) are fully validated and verified.

### Current State
- **V1.0 Milestone**: Complete and production-ready (100% verified, 121 tests passing).
- **V2.0 Milestone**: Initiating Phase 1 (Foundation & Database Models).


### Active

- [ ] **LEAVE-ALLOC**: School Admin Excel leave allocation upload and validation.
- [ ] **LEAVE-BAL**: Dynamic faculty leave balance tracking (Allocated, Used, Remaining).
- [ ] **FAC-DASH**: Personal dashboard for Faculty members showing attendance, stats, leaves, and notifications.
- [ ] **MY-ATT**: "My Attendance" history page for Faculty.
- [ ] **LEAVE-REQ**: Faculty leave application form with conflict and balance checks.
- [ ] **LEAVE-APP**: School Admin leave approval/rejection interface with reasons.
- [ ] **LEAVE-INT**: Automatic integration of approved leaves into check-in/out logs (`LEAVE` status).
- [ ] **LEAVE-NOTIF**: In-app notifications for leave submission/approval/rejection.
- [ ] **LEAVE-OVERLAP**: Validation rules to prevent overlapping leave requests.
- [ ] **LEAVE-HOL**: Respect working schedule and holiday calendar in leave balance deductions.
- [ ] **SEC-V2**: Multi-tenant isolation and strict role permission boundaries across all V2 paths.

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
- **Tech Stack**: Python, Django backend, PostgreSQL database, Tailwind CSS, Vanilla JavaScript (browser MediaDevices camera API), Django HTML templates.
- **Architecture**: Modular Django monolith with clean app boundaries and tenant-middleware context resolution.
- **Biometric & Privacy**: Biometric vector storage, data minimization, compliance readiness, audit logging, secrets in environment variables.

## Constraints

- **Tech Stack**: Django templates + Tailwind CSS + Vanilla JS — NO React/Vue/Angular SPA frameworks.
- **Database**: PostgreSQL with strict multi-tenant isolation.
- **Hardware**: Standard webcam devices (built-in laptop webcams during development).
- **Multi-Tenancy**: Subdomain-based tenant resolution; isolation enforced at data-access layer.
- **Privacy & Roles**: Platform Super Admin must NOT have access to individual faculty records or face biometric data.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Django Monolith + Tailwind + Vanilla JS | Server-rendered templates eliminate SPA overhead while maintaining fast, responsive UX and high security | — Pending |
| Multi-tenant Subdomain Routing | Provides isolated identity and clean data separation (`school.ourapp.com`) | — Pending |
| Biometric Embeddings over Raw Images | Protects privacy, minimizes data footprint, and avoids compliance liability | — Pending |
| Super Admin Data Access Restriction | Ensures customer trust by preventing platform admins from viewing faculty attendance/biometric records | — Pending |
| Faculty Face-only Attendance Interaction | Streamlines daily check-in/check-out; no password login needed for attendance scanning | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-11 after initialization*
