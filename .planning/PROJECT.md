# School Faculty Face Attendance SaaS (StudentERP1 V1)

## What This Is

A production-minded, multi-tenant SaaS platform for schools centered on webcam-based face recognition for faculty check-in and check-out attendance. Built with Django, PostgreSQL, Tailwind CSS, and Vanilla JavaScript, it offers isolated tenant environments (`school.ourapp.com`), configurable working schedules and late rules, audit logging for attendance integrity, and an authorized school admin dashboard, along with a public company landing page and school self-registration.

## Core Value

Allow school faculty to mark accurate check-in and check-out attendance using face recognition through a webcam with strict multi-tenant isolation, while giving authorized school administrators complete attendance management, rule configuration, and reporting.

## Requirements

### Validated

(None yet — ship to validate)

### Current State
- **Phase 1 Complete**: Django 5.1 foundation initialized with split settings (`django-environ`), PostgreSQL DB config, modular `apps/` structure, `TimeStampedModel` mixin, Tailwind CSS 3.4 CLI compilation, and Minimal White & Gray `base.html` template layout.

### Active

- [ ] **TENANT-01**: Multi-tenant isolation enforced at database, backend, and data-access layers ensuring complete data separation between schools
- [ ] **TENANT-02**: Subdomain-based tenant resolution (`schoolname.ourapp.com`) with secure routing and fallback handling
- [ ] **LANDING-01**: Public landing page (`ourapp.com`) showcasing product benefits, face attendance feature highlights, security positioning, pricing structure, FAQ, and "Register Your School" CTA
- [ ] **REG-01**: School self-registration flow capturing school metadata and admin credentials, initializing tenant schema/environment, and redirecting to tenant domain
- [ ] **AUTH-01**: Role-based access control (Platform Super Admin, School Admin, Faculty) with strict permission enforcement
- [ ] **AUTH-02**: Platform Super Admin account lifecycle and school activation management strictly prohibited from accessing faculty records, attendance logs, or face data
- [ ] **AUTH-03**: Secure School Admin conventional authentication (Email + Password, CSRF, session handling, password hashing)
- [ ] **FAC-01**: School Admin faculty management (Create, Edit, Deactivate/Remove, View Faculty list) scoped strictly to tenant
- [ ] **FACE-01**: Face registration workflow for School Admin to capture faculty face via webcam and generate secure biometric face representations/embeddings
- [ ] **FACE-02**: Face processing & matching engine evaluated for accuracy, CPU efficiency, Python/Django compatibility, and cloud deployment practicality
- [ ] **ATT-01**: Face-based attendance scanning interface using webcam with real-time camera state, detection feedback, scan result cues, and anti-spoofing/liveness considerations
- [ ] **ATT-02**: Check-in and check-out attendance state engine enforcing valid state transitions and preventing duplicate scans
- [ ] **ATT-03**: Exception and edge case handling (unknown face, recognition failure, late arrival, early departure, missing check-out, non-working day, holiday)
- [ ] **SCHED-01**: Configurable school working schedule engine supporting day-specific working hours, full-day/half-day designations, and date-specific exceptions (holidays)
- [ ] **SCHED-02**: Configurable late threshold & grace period engine calculating present, late, early departure, and half-day statuses automatically
- [ ] **AUDIT-01**: Attendance integrity & audit logging preserving original records, recording admin corrections with actor, timestamp, and reason
- [ ] **RPT-01**: School Admin reporting dashboard providing today's attendance, faculty-wise history, date-range reports, present/absent/late counts, working duration, and monthly summaries
- [ ] **SEC-01**: Django security hardening (CSRF, XSS prevention, SQL injection protection, rate limiting, audit logging, HTTPS enforcement, secrets via environment variables)

### Out of Scope

- [ ] **Student Attendance** — Deferred to future milestone to keep V1 focused exclusively on faculty attendance MVP
- [ ] **Student Management** — Deferred to future school management module
- [ ] **School Bus Tracking** — Deferred to future transport module
- [ ] **Parent Notifications / Communication Portal** — Deferred to future communication module
- [ ] **Fees & Tuition Management** — Deferred to future finance module
- [ ] **Payroll & Payroll Integration** — Deferred to future HR module
- [ ] **Learning Management System (LMS)** — Deferred to future academic module
- [ ] **Exams & Grading** — Deferred to future academic module
- [ ] **Chatbots / AI Assistants** — Unnecessary complexity for core biometric attendance product
- [ ] **Native Mobile Applications (iOS/Android)** — Web application with responsive UI is the V1 focus
- [ ] **Permanent Raw Facial Photo Storage** — Only biometric embeddings/vectors stored to protect privacy and minimize storage

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
