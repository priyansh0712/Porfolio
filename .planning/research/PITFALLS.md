# Pitfalls Research

**Domain:** Multi-Tenant School Faculty Face Attendance SaaS
**Researched:** 2026-08-11
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Cross-Tenant Data Leakage via Unscoped Queries

**What goes wrong:**
An admin at School A modifies the URL ID parameter (e.g. `/admin/faculty/42/edit`) or submits an API payload with `faculty_id=42` belonging to School B, and the server fetches/edits School B's record without validating `tenant_id`.

**Why it happens:**
Developers rely on generic `get_object_or_404(Faculty, id=pk)` without enforcing `tenant=request.tenant`.

**How to avoid:**
Use custom tenant-aware Django ORM models and managers that automatically append `filter(tenant=request.tenant)` on all queries, or use `django-tenants` PostgreSQL schema separation.

**Warning signs:**
Unit tests passing when accessing endpoints using explicit IDs across different tenant test fixtures.

**Phase to address:**
Phase 3 (Multi-Tenant Infrastructure) & Phase 4 (RBAC & Auth Security).

---

### Pitfall 2: Biometric Privacy & Legal Exposure from Photo Storage

**What goes wrong:**
Developers save raw webcam JPEG uploads to disk or S3 to "debug" face recognition. A database/storage breach leaks recognizable high-resolution photos of school staff, creating severe legal/regulatory liability (BIPA, GDPR, privacy laws).

**Why it happens:**
It seems convenient during early development to inspect uploaded images.

**How to avoid:**
Do NOT store raw photos permanently. Convert incoming image buffers immediately in memory to a 512-dimensional float array (ArcFace vector) and discard the image buffer from RAM.

**Warning signs:**
`MediaRoot` or S3 buckets storing image files with faculty names/IDs.

**Phase to address:**
Phase 6 (Face Registration & Biometric Pipeline).

---

### Pitfall 3: Rapid Double-Scanning & Check-in Race Conditions

**What goes wrong:**
A faculty member stands in front of the camera for 3 seconds. The webcam sends 10 frames to the server. The server processes multiple parallel requests and creates 5 check-in rows or immediate check-in AND check-out rows simultaneously.

**Why it happens:**
Lack of scan cooldown locks and missing database unique constraints.

**How to avoid:**
- Implement a 2-minute scan cooldown lock per faculty member using Redis/cache key.
- Enforce database unique constraint on `(tenant_id, faculty_id, date, scan_type)` for single daily check-ins/check-outs unless manually overridden.
- Handle state transitions cleanly (Cannot Check-Out if Check-In doesn't exist; Cannot Check-In twice on the same day).

**Warning signs:**
Multiple attendance records created within seconds of each other in test environments.

**Phase to address:**
Phase 7 (Face-based Check-In/Check-Out Engine).

---

### Pitfall 4: Platform Super Admin Privacy Leakage

**What goes wrong:**
Super Admin dashboard displays a master table of all faculty names, attendance logs, and biometric status across all schools.

**Why it happens:**
Using standard Django Admin default registration without customizing model access rules.

**How to avoid:**
Explicitly unregister or restrict tenant models (`Faculty`, `AttendanceRecord`, `FacultyFaceVector`) in Django Admin for Super Admin users. Super Admin must only see school tenant metadata (school name, admin email, subscription status, active status).

**Warning signs:**
Super Admin views displaying tenant operational tables.

**Phase to address:**
Phase 4 (Authentication & RBAC).

---

### Pitfall 5: Hardcoded Working Schedules & Weekend Assumptions

**What goes wrong:**
The system assumes Monday-Friday 9:00 AM - 5:00 PM is universal. A school operating on Saturdays or with half-day schedules marks all Saturday faculty as "Absent" or fails to calculate late thresholds.

**Why it happens:**
Hardcoding `datetime.weekday()` checks in python code.

**How to avoid:**
Build a flexible `WorkingSchedule` model allowing School Admins to set custom working/non-working status, start times, end times, and grace periods for each day of the week, plus a `DateException` table for holidays.

**Warning signs:**
If-statements checking `if date.weekday() < 5:` in business logic.

**Phase to address:**
Phase 8 (Working Schedules & Attendance Business Rules).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| **Shared Table Multi-tenancy without Manager Enforcers** | Faster to set up | Catastrophic data leaks between schools | NEVER acceptable |
| **Storing Facial Images on Disk** | Easy image debugging | Biometric privacy violation, security breach hazard | Acceptable ONLY in volatile RAM during single request processing |
| **Single-day Hardcoded Grace Period** | Quick MVP logic | Schools cannot customize late rules | NEVER acceptable |
| **Direct DB Updates for Corrections** | Simple SQL update | Loss of attendance audit trail and dispute resolution | NEVER acceptable |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **O(N) Facial Vector Scanning** | Camera scan takes 3+ seconds | Index biometric vectors, filter candidates strictly by active school tenant (`N` < 500 per school) | Breaks at 10,000+ total vectors across schools |
| **Unindexed Date Queries** | Admin dashboard reports load slowly | Composite DB index on `(tenant_id, date, faculty_id)` | Breaks at 100,000+ attendance rows |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Subdomain Spoofing** | User alters `Host` header to impersonate another school | Validate host header against registered database subdomains strictly |
| **CSRF Exemption on Camera API** | Cross-site request forgery forcing fake scans | Include CSRF token in JS `fetch()` headers for camera endpoints |
| **Session Bleed Between Tenants** | Admin logged into School A accesses School B in same browser session | Scope session cookies or validate `request.user.tenant == request.tenant` on every request |

## "Looks Done But Isn't" Checklist

- [ ] **Multi-tenancy:** Verify attempting cross-tenant access via raw API returns HTTP 404/403, not data.
- [ ] **Camera Scan:** Verify camera UI gracefully shows error if webcam access is denied or lighting is poor.
- [ ] **Audit Trail:** Verify editing attendance creates an audit entry with original value, new value, admin user, timestamp, and reason.
- [ ] **Super Admin:** Verify Super Admin user cannot query faculty biometric vectors or private logs via Django Admin.

---
*Pitfalls research for: School Faculty Face Attendance SaaS*
*Researched: 2026-08-11*
