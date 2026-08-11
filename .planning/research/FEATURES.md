# Feature Research

**Domain:** Multi-Tenant School Faculty Face Attendance SaaS
**Researched:** 2026-08-11
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Public Landing Page** | Essential for SaaS positioning, feature showcase, trust building, and self-registration | LOW | `ourapp.com` with CTA "Register Your School" |
| **School Self-Registration** | Automated tenant onboarding without manual engineering intervention | MEDIUM | Generates school tenant database/schema and School Admin account |
| **Subdomain Tenant Isolation** | School users expect dedicated workspace URL identity (`school.ourapp.com`) | MEDIUM | Enforced via tenant-resolution middleware |
| **School Admin Dashboard** | Admin needs centralized place to manage faculty, schedules, and view attendance | MEDIUM | Metrics for today's present, absent, late counts, and quick actions |
| **Faculty Management (CRUD)** | Adding, updating, deactivating faculty members | LOW | Scoped strictly to logged-in school tenant |
| **Webcam Face Registration** | Admin must enroll faculty face vector during onboarding | MEDIUM | Web camera preview + face detection overlay + embedding extraction |
| **Face Check-in & Check-out** | Core faculty attendance scanning interface | HIGH | Camera feed, instant face matching, state evaluation, check-in/out result |
| **Configurable Working Schedules** | Schools operate on custom day schedules (e.g., Saturday half-day, Sunday off) | MEDIUM | Day-of-week start/end times, half-day flags, holiday exceptions |
| **Late & Grace Period Rules** | Attendance status must reflect punctuality policies accurately | LOW | Configurable grace minutes (e.g., 10 mins late threshold) |
| **Attendance History & Reports** | Admin auditing and monthly attendance review | MEDIUM | Date-wise, faculty-wise, summary export, present/absent counts |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Biometric Privacy Vector Embedding** | Eliminates storage of raw facial images; stores only mathematical embeddings | HIGH | Protects privacy, complies with biometric safety regulations, reduces database size |
| **Immutable Attendance Audit Trail** | Prevents silent data tampering; records all admin corrections with timestamp, actor, and reason | MEDIUM | Preserves original scan record alongside correction record |
| **Super Admin Privacy Isolation** | Assures schools that platform owners cannot spy on their faculty or biometric data | MEDIUM | Strict RBAC decoupling Super Admin from tenant-level operational views |
| **Real-time Scan Feedback UI** | Instant visual and sound cues for successful check-in, duplicate attempt, or unassigned face | LOW | Clear status badges, green/red frame highlights, user guidance messages |
| **Anti-Duplicate Cooldown Lock** | Prevents faculty standing in front of camera from generating multiple attendance entries | LOW | Time-based scan debounce lock per faculty per day |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Permanent Raw Image Storage** | Admins ask to view photo proof of scans | Massive privacy liability, high storage costs, GDPR/BIPA legal hazards | Store mathematical vector embeddings; provide instant visual UI verification during scan |
| **Super Admin Global Data Viewer** | Platform owners want a "god view" of all attendance | Destroys customer trust, creates single-point data breach vulnerability | Platform dashboard shows aggregate system health (active schools, total scans count) without PII |
| **SPA Frontend Framework (React/Vue)** | "Modern UI" trend | High build complexity, duplicate state, CORS issues, slow initial payload | Server-rendered Django HTML templates + Tailwind CSS + Vanilla JS for camera |
| **Student Attendance / Scope Creep** | Future expansion vision | Dilutes V1 launch speed, increases complexity 10x before faculty MVP is validated | Strict boundary: V1 is Faculty Attendance ONLY |

## Feature Dependencies

```
[Subdomain Tenant Resolution]
    └──requires──> [School Self-Registration]

[Faculty Management]
    └──requires──> [Subdomain Tenant Isolation]

[Webcam Face Registration]
    └──requires──> [Faculty Management]
                       └──requires──> [Face Processing Engine]

[Face Check-in & Check-out Engine]
    └──requires──> [Webcam Face Registration]
                       └──requires──> [Configurable Working Schedule Engine]

[Attendance Reporting & Audit Log]
    └──requires──> [Face Check-in & Check-out Engine]
```

## MVP Definition (v1 Scope)

### Launch With (v1)

- [x] **Public Landing Page & Self-Registration** — `ourapp.com` landing page and school registration flow
- [x] **Multi-Tenant Routing** — Subdomain resolution (`school.ourapp.com`) with middleware isolation
- [x] **Role-Based Access Control** — Super Admin (platform only), School Admin (tenant admin), Faculty (scan interface)
- [x] **Faculty CRUD & Face Registration** — Enroll faculty with 512-d vector embeddings
- [x] **Webcam Face Check-in & Check-out Engine** — Real-time camera recognition, state engine, duplicate prevention
- [x] **Configurable Working Schedules & Late Rules** — Custom day schedules, grace periods, holidays
- [x] **Attendance Audit Log & Reporting** — Immutable history, admin manual corrections with audit reason, daily/faculty/monthly reports

### Add After Validation (v1.x)

- [ ] **CSV / PDF Attendance Export** — Export monthly attendance sheets for school accounting
- [ ] **Date Exception Calendar UI** — Visual calendar editor for upcoming school holidays
- [ ] **Email Attendance Alerts** — Daily digest to School Admin for unexcused absentees

### Future Consideration (v2+)

- [ ] **Student Attendance Module** — Expand face recognition to student classrooms
- [ ] **Parent Notification SMS** — Automated SMS when students/faculty arrive
- [ ] **Payroll System Integration** — Export working hours to external payroll software

---
*Feature research for: School Faculty Face Attendance SaaS*
*Researched: 2026-08-11*
