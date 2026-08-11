# Stack Research

**Domain:** Multi-Tenant SaaS / Biometric Attendance System (Django)
**Researched:** 2026-08-11
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.12+ | Core Backend Language | Optimal performance, broad library support for computer vision & ML |
| **Django** | 5.1+ | Backend Framework & Monolith | Built-in ORM, robust security features, session auth, admin, rapid server-rendered templating |
| **PostgreSQL** | 16+ | Relational Database | Advanced indexing, strict data integrity constraints, JSONB support, tenant schema isolation options |
| **InsightFace / face_recognition** | Latest (ONNX runtime) | Face Detection & Vector Embedding | Fast CPU-friendly ArcFace 512-d vector extraction; highly accurate & reliable |
| **OpenCV** | 4.10+ (headless) | Image Pre-processing | Efficient webcam frame decoding, normalization, and alignment prior to embedding |
| **Tailwind CSS** | 3.4+ | UI Styling & Utility CSS | Rapid, modern UI development without JavaScript framework bloat |
| **Vanilla JavaScript** | ES6+ | Camera & DOM API Logic | Direct browser `navigator.mediaDevices.getUserMedia` integration, canvas capture, and async fetch |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **django-tenants** / Custom Tenant Middleware | 3.7+ / Custom | Multi-tenant Subdomain Resolution | Isolates school databases/schemas based on `school.ourapp.com` request host |
| **NumPy** | 2.0+ | Vector Operations | Cosine distance & Euclidean distance calculations between facial embeddings |
| **Pillow** | 10.4+ | Image File Handling | Temporary image manipulation during registration/capture |
| **django-argon2 / Argon2id** | Built-in | Password Hashing | Modern, memory-hard security for School Admin password authentication |
| **Celery + Redis** | 5.4+ / 7.2+ | Async Task Queue | Deferred report generation, audit trail archiving, and background cleanups |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Docker & Docker Compose** | Local Postgres & Redis containerization | Ensures identical dev and production database/cache setups |
| **pytest-django** | Automated Unit & Integration Testing | Test tenant isolation, authentication, attendance state engine, and permission boundaries |
| **uv** | Python Package Management | Lightning-fast virtualenv creation and dependency resolution |

## Installation

```bash
# Core Dependencies
pip install django psycopg[binary] insightface opencv-python-headless numpy pillow

# Multi-tenancy & Security
pip install django-tenants argon2-cffi

# Background Tasks & Testing
pip install celery redis pytest pytest-django
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **InsightFace (ArcFace)** | `dlib` / `face_recognition` | `face_recognition` is simpler to install for quick demos, but InsightFace offers significantly higher accuracy and better CPU performance |
| **Django Server Templates** | React / Vue SPA | React is appropriate for hyper-interactive single-page dashboards, but creates duplicate routing, auth, and state overhead for a Django multi-tenant app |
| **Schema-based Multi-tenancy** | Foreign-Key / Shared Table Multi-tenancy | Shared table with `tenant_id` column is lighter for 1000s of micro-tenants, but schema-level isolation guarantees strict data separation and zero query leakage |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Raw Photo Disk Storage** | Storing facial photos on disk creates biometric compliance hazards, privacy liabilities, and storage bloat | Convert face capture to 512-float vector array instantly and store only vector embeddings |
| **React / Vue / Angular** | Specified explicitly as out of scope; introduces build tool complexity and extra API layer without benefit | Django HTML templates + Tailwind CSS + Vanilla JS camera capture |
| **Frontend Tenant Filtering** | Security vulnerability — passing all data to client and filtering in JS allows malicious tenant inspection | Server-side Tenant Middleware & DB-level Query Scoping |

## Stack Patterns by Variant

**For Local Development:**
- Use built-in laptop webcam with `getUserMedia`.
- Use local subdomains mapped via `hosts` file (`schoola.localhost:8000`).

**For Production Cloud Deployment:**
- Nginx with wildcard SSL certificates (`*.ourapp.com`).
- Gunicorn WSGI workers behind Nginx.
- PostgreSQL database with schema or row-level tenant security policies.

## Sources

- Official Django Documentation (Security, Middleware, Multi-Tenancy patterns)
- InsightFace Deep Insight Library Docs (ArcFace model specifications)
- OWASP Web Security Testing Guide (Tenant Isolation & Biometric Security)

---
*Stack research for: School Faculty Face Attendance SaaS*
*Researched: 2026-08-11*
