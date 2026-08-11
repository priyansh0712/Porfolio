# Requirements: School Faculty Face Attendance SaaS (StudentERP1 V1)

**Defined:** 2026-08-11
**Core Value:** Allow school faculty to mark accurate check-in and check-out attendance using face recognition through a webcam with strict multi-tenant isolation, while giving authorized school administrators complete attendance management, rule configuration, and reporting.

## v1 Requirements

### Tenant Management & Isolation

- [ ] **TENANT-01**: Multi-tenant data isolation enforced at database, backend service, and data-access layers ensuring complete data separation between schools
- [ ] **TENANT-02**: Subdomain-based tenant resolution (`schoolname.ourapp.com`) with secure host header validation and fallback handling

### Public Platform & Registration

- [ ] **LANDING-01**: Public landing page (`ourapp.com`) showcasing product benefits, face recognition highlights, security positioning, pricing structure, FAQ, and "Register Your School" CTA
- [ ] **REG-01**: School self-registration flow capturing school metadata and admin credentials, initializing tenant schema/environment, and redirecting to tenant domain

### Authentication & RBAC

- [ ] **AUTH-01**: Role-based access control (Platform Super Admin, School Admin, Faculty) with strict server-side permission enforcement
- [ ] **AUTH-02**: Platform Super Admin account lifecycle and school activation management strictly prohibited from accessing faculty records, attendance logs, or face data
- [ ] **AUTH-03**: Secure School Admin conventional authentication (Email + Password, CSRF protection, session handling, Argon2id password hashing)

### Faculty Management

- [ ] **FAC-01**: School Admin faculty management (Create, Edit, Deactivate/Remove, View Faculty list) scoped strictly to active tenant

### Face Registration & Biometrics

- [ ] **FACE-01**: Face registration workflow for School Admin to capture faculty face via webcam and generate secure 512-dimensional vector embeddings
- [ ] **FACE-02**: Biometric privacy pipeline processing face frames in memory and discarding image buffers immediately to guarantee zero raw facial photo storage

### Attendance Scanning & Engine

- [ ] **ATT-01**: Face-based attendance scanning interface using webcam with real-time camera state, detection feedback, scan result cues, and anti-spoofing considerations
- [ ] **ATT-02**: Check-in and check-out attendance state engine enforcing valid state transitions and preventing duplicate scans via cooldown locks
- [ ] **ATT-03**: Exception and edge case handling (unknown face, recognition failure, late arrival, early departure, missing check-out, non-working day, holiday)

### Working Schedules & Late Rules

- [ ] **SCHED-01**: Configurable school working schedule engine supporting day-specific working hours, full-day/half-day designations, and date-specific exceptions (holidays)
- [ ] **SCHED-02**: Configurable late threshold & grace period engine calculating present, late, early departure, and half-day statuses automatically

### Reporting & Audit Logging

- [ ] **RPT-01**: School Admin reporting dashboard providing today's attendance, faculty-wise history, date-range reports, present/absent/late counts, working duration, and monthly summaries
- [ ] **AUDIT-01**: Attendance integrity & audit logging preserving original records, recording admin corrections with actor, timestamp, and mandatory reason string

### Security & Hardening

- [ ] **SEC-01**: Django security hardening (CSRF, XSS prevention, SQL injection protection, rate limiting, audit logging, HTTPS enforcement, secrets via environment variables)

## v2 Requirements

### Communication & Exports

- **COMM-01**: Automated daily attendance digest email sent to School Admin
- **EXPT-01**: Monthly attendance export to CSV and PDF format for payroll and school recordkeeping
- **CAL-01**: Interactive holiday and school event calendar editor UI

## Out of Scope

| Feature | Reason |
|---------|--------|
| Student Attendance | Excluded from V1 to maintain strict focus on school faculty attendance MVP |
| Student Management | Belongs to future comprehensive school management module |
| School Bus / Transport Tracking | Belongs to future transport module |
| Parent Communication Portal / SMS | Belongs to future communication module |
| Fees & Tuition Management | Belongs to future finance module |
| Payroll Processing | Belongs to future HR module |
| Learning Management System (LMS) | Out of scope for attendance SaaS MVP |
| Exam & Grade Management | Out of scope for attendance SaaS MVP |
| Chatbots & Unnecessary AI Features | Unnecessary complexity for core biometric attendance product |
| Native Mobile Apps (iOS/Android) | Responsive web application is the V1 product scope |
| Permanent Raw Facial Photo Storage | Biometric privacy hazard; only mathematical embeddings stored |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TENANT-01 | Phase 3 | Pending |
| TENANT-02 | Phase 3 | Pending |
| LANDING-01 | Phase 2 | Pending |
| REG-01 | Phase 2 | Pending |
| AUTH-01 | Phase 4 | Pending |
| AUTH-02 | Phase 4 | Pending |
| AUTH-03 | Phase 4 | Pending |
| FAC-01 | Phase 5 | Pending |
| FACE-01 | Phase 6 | Pending |
| FACE-02 | Phase 6 | Pending |
| ATT-01 | Phase 7 | Pending |
| ATT-02 | Phase 7 | Pending |
| ATT-03 | Phase 7 | Pending |
| SCHED-01 | Phase 8 | Pending |
| SCHED-02 | Phase 8 | Pending |
| RPT-01 | Phase 9 | Pending |
| AUDIT-01 | Phase 9 | Pending |
| SEC-01 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-11*
*Last updated: 2026-08-11 after initial definition*
