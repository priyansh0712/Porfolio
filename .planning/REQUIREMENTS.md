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

### Leave Management & Allocation
- **LEAVE-ALLOC**: School Admin must be able to upload an Excel file to assign/update leave allocations for existing faculty, with validation.
- **LEAVE-BAL**: Track Allocated, Used, and Remaining leave balances per faculty member for Casual, Sick, and Paid leaves. Used/Remaining balances are computed dynamically.
- **LEAVE-REQ**: Faculty members can apply for leave via a form with validation (date ordering, overlapping checks, sufficient balance).
- **LEAVE-APP**: School Admin can review, filter, and approve or reject leave requests (rejection requires a mandatory reason).
- **LEAVE-OVERLAP**: System must reject overlapping leave requests.
- **LEAVE-HOL**: Respect school working schedules and holidays in leave request calculations (e.g. non-working days/holidays do not deduct balance).

### Faculty Dashboard & Attendance
- **FAC-DASH**: Faculty personal dashboard displaying today's attendance, summary stats, leave balances, pending requests, and notifications.
- **MY-ATT**: Faculty "My Attendance" page showing a summary of Present/Absent/Half-Day/Late/Leave counts and a detailed date-wise log.
- **LEAVE-INT**: Approved leaves automatically create/update attendance logs with status `LEAVE`, reflecting consistently in all admin/faculty views.

### notifications & Security
- **LEAVE-NOTIF**: In-app notifications when leave is submitted, approved, or rejected.
- **SEC-V2**: Strict role-based permissions (School Admin vs Faculty vs Super Admin) and multi-tenant isolation across all V2 features.

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
| Native Mobile Apps (iOS/Android) | Responsive web application is the V1/V2 product scope |
| Permanent Raw Facial Photo Storage | Biometric privacy hazard; only mathematical embeddings stored |
| WhatsApp/SMS/Email notifications | Excluded from V2 scope to keep notifications strictly in-app |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LEAVE-ALLOC | Phase 2 | Pending |
| LEAVE-BAL | Phase 3 | Pending |
| LEAVE-REQ | Phase 3 | Pending |
| LEAVE-APP | Phase 4 | Pending |
| LEAVE-OVERLAP | Phase 3 | Pending |
| LEAVE-HOL | Phase 8 | Pending |
| FAC-DASH | Phase 3 | Pending |
| MY-ATT | Phase 6 | Pending |
| LEAVE-INT | Phase 5 | Pending |
| LEAVE-NOTIF | Phase 7 | Pending |
| SEC-V2 | Phase 9 | Pending |

**Coverage:**
- v2 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-11*
*Last updated: 2026-08-16 after V2 definition*
