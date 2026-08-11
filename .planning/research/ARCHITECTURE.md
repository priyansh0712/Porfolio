# Architecture Research

**Domain:** Multi-Tenant School Faculty Face Attendance SaaS
**Researched:** 2026-08-11
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PUBLIC LAYER                                  │
│   Landing Page (ourapp.com) ──> School Self-Registration ──> Provision  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                    TENANT RESOLUTION & MIDDLEWARE                       │
│    Subdomain Request Parser (school.ourapp.com) ──> Set Tenant Context │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                      APPLICATION & BUSINESS LAYER                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ Auth & RBAC      │  │ Faculty Module   │  │ Biometrics Engine     │  │
│  │ (Admin vs Fac)   │  │ (CRUD / Enrollment)│ │ (InsightFace Vectors) │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────────┬───────────┘  │
│           │                     │                        │              │
│  ┌────────▼─────────┐  ┌────────▼─────────┐  ┌───────────▼───────────┐  │
│  │ Schedule Engine  │  │ Attendance Engine│  │ Audit & Report Engine │  │
│  │ (Hours/Grace/Hol)│  │ (CheckIn/Out State)││ (Immutable History)   │  │
│  └──────────────────┘  └──────────────────┘  └───────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                           DATA & ISOLATION LAYER                        │
│   PostgreSQL Database (Isolated Schemas or Tenant-Scoped Tables)        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Tenant Middleware** | Intercepts HTTP host header, extracts subdomain, sets active tenant context for thread/request | Django Middleware (`TenantMiddleware`) |
| **Authentication & RBAC** | Handles login, session management, CSRF checks, and enforces tenant & role permissions | Django Auth + Custom Permission Classes (`IsSchoolAdmin`, `IsPlatformSuperAdmin`) |
| **Faculty Manager** | Manages faculty profile metadata, employment status, and department tags | Django App (`apps/faculty`) |
| **Biometric Pipeline** | Decodes frame snapshot from JS, extracts ArcFace 512-d float array, compares Euclidean/Cosine distance against enrolled vectors | Django App (`apps/biometrics`) using InsightFace/OpenCV |
| **Attendance State Engine** | Evaluates scan timestamp against schedule, checks existing check-in/out records, determines status (Present, Late, Half-Day), prevents duplicates | Django App (`apps/attendance`) |
| **Schedule Engine** | Stores weekly working day configs, custom start/end times, grace period minutes, and calendar holiday exceptions | Django App (`apps/schedules`) |
| **Audit & Reporting** | Logs immutable scan events, tracks admin manual corrections (original vs edited, timestamp, reason), compiles attendance summaries | Django App (`apps/reports`) |

## Recommended Project Structure

```
StudentERP1/
├── manage.py
├── config/                     # Django Project Configuration
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                       # Modular Django Applications
│   ├── core/                   # Base models, Mixins, Utilities
│   ├── tenants/                # Tenant model, Subdomain Middleware, Domain Routing
│   ├── accounts/               # Custom User model, Auth, Roles, RBAC permissions
│   ├── public/                 # Public Landing page, Registration views
│   ├── faculty/                # Faculty profile management
│   ├── biometrics/             # Face vector extraction, embedding store, matcher
│   ├── schedules/              # Working days, hours, grace periods, holidays
│   ├── attendance/             # Check-in/out engine, state machine, scan logs
│   └── reports/                # Admin dashboards, summary views, audit logs
├── templates/                  # Server-rendered Django HTML Templates
│   ├── base.html
│   ├── public/                 # Landing page & registration templates
│   ├── admin/                  # School admin dashboard & management
│   ├── attendance/             # Camera scanning UI
│   └── reports/                # Report tables & charts
├── static/                     # Static Assets
│   ├── css/                    # Tailwind CSS output
│   └── js/                     # Camera capture API, UI state handler
└── tests/                      # Automated Test Suite
    ├── test_tenants.py
    ├── test_auth.py
    ├── test_attendance.py
    └── test_biometrics.py
```

## Architectural Patterns

### Pattern 1: Tenant Context Middleware & Scoped QuerySet

**What:** Middleware intercepts request hostname (`schoolname.ourapp.com`), loads the `Tenant` object, and binds it to `request.tenant`. All database managers filter automatically by `tenant=request.tenant`.

**Code Example:**
```python
# apps/tenants/middleware.py
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        hostname = request.get_host().split(':')[0]
        subdomain = hostname.split('.')[0] if '.' in hostname else None
        
        if subdomain and subdomain != 'ourapp' and subdomain != 'www':
            request.tenant = Tenant.objects.filter(subdomain=subdomain, is_active=True).first()
            if not request.tenant:
                raise Http404("School tenant not found")
        else:
            request.tenant = None
            
        return self.get_response(request)
```

### Pattern 2: Biometric Embedding Matcher (No Raw Image)

**What:** Facial frames captured from the HTML5 canvas are sent via HTTP POST as Base64 JPEG. The server processes the frame, extracts a 512-dimensional float vector, calculates Euclidean distance against stored vectors for the active tenant, and discards the image immediately.

**Code Example:**
```python
# apps/biometrics/services.py
def identify_faculty_face(tenant, frame_bytes):
    # Extract ArcFace embedding from input frame
    embedding = face_app.get_embedding(frame_bytes)
    if embedding is None:
        return None, "NO_FACE_DETECTED"
    
    enrolled_faculties = FacultyFaceVector.objects.filter(tenant=tenant)
    best_match = None
    min_distance = 0.6  # Cosine distance threshold

    for record in enrolled_faculties:
        dist = calculate_cosine_distance(embedding, record.vector)
        if dist < min_distance:
            min_distance = dist
            best_match = record.faculty
            
    return best_match, "SUCCESS"
```

### Pattern 3: Immutable Attendance Record + Audit Log

**What:** Attendance records cannot be overwritten directly. If an admin manually corrects an entry, the system saves an `AttendanceCorrection` audit entry detailing who made the change, the old status, the new status, the timestamp, and the mandatory reason string.

## Data Flow

### Attendance Scan Request Flow

```
[Faculty appears in front of Camera]
    ↓
[Vanilla JS captures Canvas Frame] ──(Base64 POST)──> [Django Attendance Endpoint]
                                                             ↓
                                                    [TenantMiddleware validates school tenant]
                                                             ↓
                                                    [Biometrics Engine extracts & matches vector]
                                                             ↓
                                                    [Schedule Engine fetches today's rules]
                                                             ↓
                                                    [Attendance Engine checks existing check-in/out]
                                                             ↓
                                                    [DB write: AttendanceRecord (Present/Late)]
                                                             ↓
[JS UI renders Result Badge & Sound] <──(JSON Response)─────┘
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **1-50 Schools** (MVP) | Single Django monolith + PostgreSQL container. Monolithic server handling camera recognition synchronously |
| **50-500 Schools** | Separate background worker nodes (Celery) for heavy batch reports. DB connection pooling (pgBouncer) |
| **500+ Schools** | Dedicated inference microservice (FastAPI + ONNX Runtime) for face embedding extraction |

---
*Architecture research for: School Faculty Face Attendance SaaS*
*Researched: 2026-08-11*
