---
phase: 04-authentication-role-based-access-control-rbac
status: complete
current_test: 5
total_tests: 5
results:
  - test: 1
    name: "School Self-Registration & Admin Creation"
    status: pass
  - test: 2
    name: "Tenant Subdomain School Admin Login"
    status: pass
  - test: 3
    name: "Cross-Tenant Login Rejection"
    status: pass
  - test: 4
    name: "Super Admin Root Domain Login & Dashboard"
    status: pass
  - test: 5
    name: "Super Admin Privacy Boundary Defense (HTTP 403)"
    status: pass
---

# Phase 4 UAT: Authentication & Role-Based Access Control (RBAC)

## Tests

### 1. School Self-Registration & Admin Creation
- **Expected**: Visit `localhost:8000/register/` (root domain), register a new school (e.g. `Greenwood High`, subdomain `greenwood`, admin email `admin@greenwood.com`, password `Password123!`). Form submits successfully, redirects to registration success page.

### 2. Tenant Subdomain School Admin Login
- **Expected**: Visit `greenwood.localhost:8000/login/`. Glassmorphism login card displays "Greenwood High" branding and `greenwood.ourapp.com` badge. Enter `admin@greenwood.com` and `Password123!`. Login succeeds and redirects to `/dashboard/` displaying the School Admin welcome banner.

### 3. Cross-Tenant Login Rejection
- **Expected**: On `greenwood.localhost:8000/login/`, attempt to log in with an admin email from a different school or Super Admin email. Login is rejected with a flash error alert ("Please enter a correct email address and password").

### 4. Super Admin Root Domain Login & Dashboard
- **Expected**: Visit `localhost:8000/login/` (root domain). Login card displays "Platform Login / Super Admin Access". Log in with Super Admin credentials. Redirects to `localhost:8000/superadmin/` displaying the School Tenant table and "🔒 No Faculty Data Access" privacy badge.

### 5. Super Admin Privacy Boundary Defense (HTTP 403)
- **Expected**: While logged in as Super Admin on `localhost:8000`, attempt to visit `/dashboard/`, `/faculty/`, `/attendance/`, or `/biometrics/`. Access is blocked immediately with an HTTP 403 Forbidden error response.

## Current Test

**Test 1: School Self-Registration & Admin Creation**
- **Expected**: Visit `localhost:8000/register/` on root domain, register a school (e.g. `Greenwood High`, subdomain `greenwood`, admin email `admin@greenwood.com`, password `Password123!`). Form submits successfully, redirects to registration success page without any DB constraint errors.
