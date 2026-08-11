# Project Research Summary

**Project:** School Faculty Face Attendance SaaS (StudentERP1 V1)
**Domain:** Multi-Tenant SaaS / Face Recognition Attendance Engine
**Researched:** 2026-08-11
**Confidence:** HIGH

## Executive Summary

The project is a production-minded multi-tenant SaaS application designed for school faculty face-based attendance management. Built as a modular Django monolith with PostgreSQL, Tailwind CSS, and Vanilla JavaScript, it solves the core problem of accurate, fraud-proof faculty time tracking via webcams without expensive physical hardware.

Key technical requirements include strict multi-tenant isolation (subdomain-based `school.ourapp.com`), a privacy-first biometric vector engine (storing ArcFace 512-d embeddings, no permanent raw photo storage), configurable school schedules and late rules, immutable attendance audit logging, and role-based access control where Platform Super Admins are strictly blocked from viewing private school attendance or biometric data.

The primary architectural risk is cross-tenant data leakage and biometric privacy liabilities. These are mitigated by combining database-level tenant query scoping, instant image-to-vector conversion, strict permission decorators, and automated permission isolation tests across all phases.

## Key Findings

### Recommended Stack

- **Backend Framework:** Django 5.1+ (Python 3.12+) with PostgreSQL 16
- **Biometric Pipeline:** InsightFace (ArcFace model on ONNX Runtime) + OpenCV headless + NumPy
- **Frontend Layer:** Django HTML Templates + Tailwind CSS 3.4 + Vanilla JS (MediaDevices API)
- **Multi-Tenancy:** Subdomain Middleware + Tenant-aware ORM Managers (`school.ourapp.com`)
- **Security & Auth:** Django Auth, Argon2id password hashing, CSRF tokens, strict RBAC

### Expected Features

**Table Stakes (V1 Scope):**
- Public landing page (`ourapp.com`) with school self-registration
- Isolated school subdomain environments (`school.ourapp.com`)
- School Admin dashboard, faculty CRUD, and webcam face enrollment
- Real-time webcam check-in / check-out scanning interface
- Configurable working schedules (custom days, hours, grace periods, holidays)
- Attendance history, daily summaries, and immutable audit logs

**Defer to V2+:**
- Student attendance & student management modules
- School bus tracking, parent SMS alerts, LMS, exams, fees, payroll

### Critical Pitfalls to Avoid

1. **Cross-Tenant Data Leakage:** Prevented by automatic tenant ORM scoping & middleware validation.
2. **Biometric Privacy Violation:** Prevented by storing 512-d vector embeddings only — no raw images saved on disk.
3. **Scan Duplicate Race Conditions:** Prevented by database unique constraints & Redis scan debounce locks.
4. **Super Admin Privacy Leak:** Prevented by strict RBAC unregistering tenant operational views from Super Admin.

## Implications for Roadmap

Based on dependency analysis, domain research, and risk mitigation, the recommended 10-phase execution roadmap is:

### Phase 1: Project Foundation & Architecture Setup
- **Delivers:** Django project setup, PostgreSQL config, Tailwind CSS compilation, core app structure, environment variable handling.
- **Avoids:** Unstructured codebase and global state pollution.

### Phase 2: Public Platform & School Registration
- **Delivers:** Public landing page (`ourapp.com`), features/security marketing UI, school registration form, tenant database initialization.
- **Addresses:** LANDING-01, REG-01.

### Phase 3: Multi-Tenant Subdomain Infrastructure
- **Delivers:** Subdomain resolution middleware (`school.ourapp.com`), tenant context manager, tenant isolation test suite.
- **Addresses:** TENANT-01, TENANT-02.
- **Avoids:** Pitfall 1 (Cross-tenant data leakage).

### Phase 4: Authentication & Role-Based Access Control (RBAC)
- **Delivers:** School Admin auth, Super Admin platform isolation, RBAC permission enforcers, CSRF & session security.
- **Addresses:** AUTH-01, AUTH-02, AUTH-03.
- **Avoids:** Pitfall 4 (Super Admin privacy leak).

### Phase 5: Faculty Management Suite
- **Delivers:** School Admin faculty CRUD, department tagging, active/deactive status, faculty list views scoped to tenant.
- **Addresses:** FAC-01.

### Phase 6: Face Registration & Biometric Pipeline
- **Delivers:** Webcam face capture UI, InsightFace ArcFace vector extraction, 512-d vector DB store, zero raw image storage pipeline.
- **Addresses:** FACE-01, FACE-02.
- **Avoids:** Pitfall 2 (Biometric photo storage liability).

### Phase 7: Face-Based Check-In & Check-Out Engine
- **Delivers:** Webcam scanning screen, real-time face identification, state engine (Check-in vs Check-out), scan debounce lock.
- **Addresses:** ATT-01, ATT-02, ATT-03.
- **Avoids:** Pitfall 3 (Rapid duplicate scanning).

### Phase 8: Working Schedules & Attendance Business Rules
- **Delivers:** Configurable day-of-week working hours, full/half-day flags, grace period late calculator, date exceptions (holidays).
- **Addresses:** SCHED-01, SCHED-02.
- **Avoids:** Pitfall 5 (Hardcoded schedule assumptions).

### Phase 9: Admin Dashboard, Reports & Audit Log
- **Delivers:** Today's attendance widget, date-wise history, faculty monthly summary, admin manual correction modal with mandatory audit reason logging.
- **Addresses:** AUDIT-01, RPT-01.

### Phase 10: Security Hardening, Verification & Cloud Readiness
- **Delivers:** Cross-tenant security audit, rate limiting, automated test suite completion, Docker production setup, deployment guide.
- **Addresses:** SEC-01.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Django + Postgres + InsightFace + Tailwind/JS is standard, highly reliable |
| Features | HIGH | V1 boundaries explicitly clear; out-of-scope items defined |
| Architecture | HIGH | Monolithic layered Django architecture with tenant middleware |
| Pitfalls | HIGH | Specific security, legal, and multi-tenant pitfalls identified and mapped to phases |

**Overall confidence:** HIGH

---
*Research completed: 2026-08-11*
*Ready for roadmap: yes*
