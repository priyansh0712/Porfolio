# Roadmap: School Faculty Face Attendance SaaS (StudentERP1 V1)

## Overview

This roadmap outlines the 10-phase build sequence for a production-minded multi-tenant SaaS application for school faculty face-based attendance. The development moves systematically from foundation architecture and public school registration, through multi-tenant subdomain isolation and RBAC security, to faculty management, face vector registration, face-based check-in/out engine, configurable schedules/late rules, admin reporting with audit logging, and security hardening.

## Phases

- [ ] **Phase 1: Project Foundation & Base Architecture** - Django project setup, PostgreSQL, Tailwind CSS compilation, core apps structure, and base layouts.
- [x] **Phase 2: Public Landing Page & School Registration** - Public marketing landing page (`ourapp.com`) and school self-registration onboarding.
- [ ] **Phase 3: Multi-Tenant Subdomain Infrastructure** - Subdomain resolution middleware (`school.ourapp.com`), tenant context manager, and database isolation enforcement.
- [ ] **Phase 4: Authentication & Role-Based Access Control (RBAC)** - School Admin login, Super Admin platform isolation, RBAC permission enforcers, and session security.
- [ ] **Phase 5: Faculty Management Suite** - School Admin faculty CRUD, department tagging, and active/deactive status management scoped to tenant.
- [ ] **Phase 6: Face Registration & Biometric Pipeline** - Webcam face enrollment interface, InsightFace ArcFace 512-d vector extraction, and zero-raw-photo biometric pipeline.
- [ ] **Phase 7: Face-Based Check-In & Check-Out Engine** - Real-time webcam scanning interface, face matching, scan state transition engine, and debounce locks.
- [ ] **Phase 8: Working Schedules & Attendance Business Rules** - Configurable day-of-week working hours, grace period late calculator, half-day rules, and holiday exceptions.
- [ ] **Phase 9: Admin Dashboard, Reports & Audit Log** - Today's attendance dashboard, date/faculty reports, and immutable admin correction audit trail.
- [ ] **Phase 10: Security Hardening, Verification & Production Readiness** - Full security audit, rate limiting, automated test suite completion, Docker production setup, and deployment guide.

## Phase Details

### Phase 1: Project Foundation & Base Architecture
**Goal**: Initialize Django 5.1 project with PostgreSQL, Tailwind CSS compilation, core app structure, environment configuration, and base layout templates.
**Depends on**: Nothing (first phase)
**Requirements**: Core project foundation
**Success Criteria** (what must be TRUE):
  1. Django application runs locally connected to PostgreSQL inside `uv` managed environment.
  2. Tailwind CSS compiles cleanly into static CSS assets with live rebuild watcher.
  3. Responsive base HTML template layout renders clean navigation header and main container.
**Plans**: 2 plans

Plans:
- [x] 01-01: Django project initialization, environment settings (`config/settings/`), PostgreSQL DB connection, and app directory setup
- [x] 01-02: Tailwind CSS 3.4 setup, base layout templates (`base.html`, navigation, footer), and static asset pipeline

### Phase 2: Public Landing Page & School Registration
**Goal**: Deliver public landing page (`ourapp.com`) and school self-registration flow creating school tenant records and initial School Admin accounts.
**Depends on**: Phase 1
**Requirements**: LANDING-01, REG-01
**Success Criteria** (what must be TRUE):
  1. Visitors can browse public landing page detailing face attendance benefits, security positioning, pricing structure, and FAQ.
  2. School administrators can submit registration form to create a new school tenant and primary admin account.
  3. Registration automatically initializes default school settings and redirects to tenant onboarding view.
**Plans**: 2 plans

Plans:
- [x] 02-01: Public landing page view, marketing sections (Hero, Features, Security, Pricing, FAQ), and CTA layout
- [x] 02-02: School self-registration form, validation, tenant creation service, and admin user initialization

### Phase 3: Multi-Tenant Subdomain Infrastructure
**Goal**: Build subdomain-based tenant resolution middleware (`school.ourapp.com`) and tenant-aware database query scoping to ensure total tenant isolation.
**Depends on**: Phase 2
**Requirements**: TENANT-01, TENANT-02
**Success Criteria** (what must be TRUE):
  1. HTTP requests to `schoolname.ourapp.com` resolve automatically to the corresponding school tenant context.
  2. Queries across models are strictly filtered by active tenant; attempts to access another school's data return HTTP 404/403.
  3. Automated test suite verifies zero cross-tenant query leaks.
**Plans**: 2 plans

Plans:
- [x] 03-01: Subdomain resolution middleware (`TenantMiddleware`), domain model, and request context binding
- [x] 03-02: Tenant-aware ORM manager/model mixin (`TenantModelMixin`), view enforcers, and cross-tenant isolation test suite

### Phase 4: Authentication & Role-Based Access Control (RBAC)
**Goal**: Implement strict role-based access control (Platform Super Admin, School Admin, Faculty) with Argon2id password security, session protection, and Super Admin privacy boundaries.
**Depends on**: Phase 3
**Requirements**: AUTH-01, AUTH-02, AUTH-03
**Success Criteria** (what must be TRUE):
  1. School Admins can log into their tenant subdomain securely with email/password and session persistence.
  2. Super Admins can manage school account lifecycles but are strictly blocked from accessing individual faculty records or attendance data.
  3. Unauthenticated or unauthorized role access attempts are rejected across all routes.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Custom User model, Roles (Super Admin, School Admin, Faculty), Argon2id hashing, and School Admin authentication views
- [ ] 04-02: Super Admin platform management panel and RBAC permission decorators (`IsSchoolAdmin`, `IsPlatformSuperAdmin`) with privacy boundaries

### Phase 5: Faculty Management Suite
**Goal**: Provide School Admins with comprehensive faculty management capabilities (create, update, deactivate, list view) scoped to their tenant.
**Depends on**: Phase 4
**Requirements**: FAC-01
**Success Criteria** (what must be TRUE):
  1. School Admin can add new faculty members with department, designation, and contact info.
  2. School Admin can edit or deactivate existing faculty without deleting historical records.
  3. Faculty list view displays current employment status and face enrollment status.
**Plans**: 2 plans

Plans:
- [ ] 05-01: Faculty model, forms, and tenant-scoped CRUD views (Create, Edit, List, Detail)
- [ ] 05-02: Faculty status management (Active, Inactive), department tagging, and School Admin faculty management UI

### Phase 6: Face Registration & Biometric Pipeline
**Goal**: Implement webcam face enrollment interface for School Admins, InsightFace ArcFace vector extraction, and zero-raw-photo biometric storage pipeline.
**Depends on**: Phase 5
**Requirements**: FACE-01, FACE-02
**Success Criteria** (what must be TRUE):
  1. School Admin can launch webcam face enrollment modal to capture faculty face sample.
  2. System extracts 512-dimensional vector embedding in memory and saves vector to database.
  3. Incoming facial image buffer is discarded immediately; zero raw photos stored on disk or cloud.
**Plans**: 2 plans

Plans:
- [ ] 06-01: Browser webcam capture JS component (`getUserMedia`), HTML5 Canvas frame snapshot extraction, and API endpoint
- [ ] 06-02: InsightFace ArcFace embedding service, `FacultyFaceVector` model, Euclidean/Cosine distance matcher, and enrollment UI

### Phase 7: Face-Based Check-In & Check-Out Engine
**Goal**: Deliver real-time webcam scanning screen for faculty check-in/check-out with instant face vector matching, scan debounce locks, and state transition handling.
**Depends on**: Phase 6
**Requirements**: ATT-01, ATT-02, ATT-03
**Success Criteria** (what must be TRUE):
  1. Faculty can stand in front of webcam and receive instant recognition feedback (face detected, name identified, scan success badge).
  2. First valid scan of the day creates Check-In record; subsequent scan later creates Check-Out record.
  3. Scan debounce lock prevents duplicate attendance records from rapid consecutive camera frames.
**Plans**: 3 plans

Plans:
- [ ] 07-01: Real-time attendance camera scanning screen template, Vanilla JS video loop, and visual status badges
- [ ] 07-02: Face identification & scan engine (matching vector against tenant vectors, scan state determination)
- [ ] 07-03: Attendance record state machine (Check-In vs Check-Out), scan debounce lock, and edge case error handlers

### Phase 8: Working Schedules & Attendance Business Rules
**Goal**: Implement configurable school working schedule engine (days of week, start/end times, full/half-day flags, grace periods, holidays) and status calculation.
**Depends on**: Phase 7
**Requirements**: SCHED-01, SCHED-02
**Success Criteria** (what must be TRUE):
  1. School Admin can configure day-specific working hours, grace period threshold (e.g. 10 mins), and half-day hours.
  2. System automatically marks scans as Present, Late, Half-Day, or Early Departure based on school schedule.
  3. Date exceptions (holidays) skip attendance requirement and prevent invalid absent tags.
**Plans**: 2 plans

Plans:
- [ ] 08-01: `WorkingSchedule` and `HolidayException` models, admin schedule configuration UI, and day-of-week settings
- [ ] 08-02: Punctuality calculator engine (evaluating scan timestamps against schedule, grace period, late threshold, half-day, holiday)

### Phase 9: Admin Dashboard, Reports & Audit Log
**Goal**: Deliver School Admin attendance dashboard, daily summaries, faculty history views, and immutable correction audit trail.
**Depends on**: Phase 8
**Requirements**: RPT-01, AUDIT-01
**Success Criteria** (what must be TRUE):
  1. School Admin dashboard shows real-time metrics for today's present, absent, late, and check-in counts.
  2. Date-wise and faculty-wise attendance reports show daily working duration and punctuality logs.
  3. Admin manual corrections preserve original record and store audit log entry with timestamp, admin ID, and mandatory reason string.
**Plans**: 2 plans

Plans:
- [ ] 09-01: School Admin dashboard metrics widgets, today's attendance feed, and date-range / faculty-wise reporting tables
- [ ] 09-02: Attendance correction modal, `AttendanceCorrection` audit log model, and immutable audit history viewer

### Phase 10: Security Hardening, Verification & Production Readiness
**Goal**: Complete full security audit (CSRF, XSS, SQLi, rate limiting, host validation), automated test suite execution, Docker containerization, and production documentation.
**Depends on**: Phase 9
**Requirements**: SEC-01
**Success Criteria** (what must be TRUE):
  1. Security audit confirms rate limiting on scan endpoints, wildcard SSL configuration, and environment variable secret enforcement.
  2. 100% of automated tests (tenant isolation, RBAC, biometric pipeline, state engine) pass cleanly.
  3. Complete production Docker Compose setup ready for deployment.
**Plans**: 2 plans

Plans:
- [ ] 10-01: Django security hardening (rate limiting, security headers, input sanitization enforcers, CSRF validation) and test suite execution
- [ ] 10-02: Production Docker setup (`Dockerfile`, `docker-compose.yml`, Nginx config, Gunicorn WSGI), secrets configuration, and deployment documentation

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Foundation & Base Architecture | 0/2 | Not started | - |
| 2. Public Landing Page & School Registration | 2/2 | Complete | 2026-08-11 |
| 3. Multi-Tenant Subdomain Infrastructure | 0/2 | Not started | - |
| 4. Authentication & Role-Based Access Control (RBAC) | 0/2 | Not started | - |
| 5. Faculty Management Suite | 0/2 | Not started | - |
| 6. Face Registration & Biometric Pipeline | 0/2 | Not started | - |
| 7. Face-Based Check-In & Check-Out Engine | 0/3 | Not started | - |
| 8. Working Schedules & Attendance Business Rules | 0/2 | Not started | - |
| 9. Admin Dashboard, Reports & Audit Log | 0/2 | Not started | - |
| 10. Security Hardening, Verification & Production Readiness | 0/2 | Not started | - |

---
*Roadmap created: 2026-08-11*
