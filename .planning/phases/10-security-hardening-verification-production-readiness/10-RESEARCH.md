# Phase 10 Research: Security Hardening, Verification & Production Readiness

## Executive Summary
Phase 10 completes the technical requirements for StudentERP V1.0 production launch. This research covers endpoint rate-limiting patterns in Django, production settings architecture, Docker Compose orchestration for PostgreSQL 16 + Redis 7 + Gunicorn + Nginx, and automated verification criteria.

---

## 1. Rate Limiting Architecture

### Sensitive Endpoints Requiring Rate Limits
1. `/login/`: Prevents brute-force credential stuffing attacks (limit: 5 attempts/min per IP).
2. `/biometrics/extract/`: Prevents resource exhaustion from intensive OpenCV decoding & ArcFace vector processing (limit: 10 extractions/min per IP).
3. `/attendance/scan/`: Allows high-frequency kiosk auto-scans while blocking denial-of-service spam (limit: 60 scans/min per IP).

### Implementation Pattern
- Using a lightweight IP-based sliding window rate limiter utility (`apps.core.ratelimit.ratelimit_decorator` or cache-backed rate limiter) using Django's cache backend (Redis / LocMemCache in dev).

---

## 2. Production Settings & Security Headers

### Module Layout
- `config/settings/base.py`: Shared configurations.
- `config/settings/development.py`: Local dev settings (`DEBUG = True`, `localhost` hosts).
- `config/settings/production.py`: Production settings (`DEBUG = False`, `os.environ` secrets, HTTPS SSL headers).

---

## 3. Docker Infrastructure Stack

- **`Dockerfile`**:
  - Base: `python:3.12-slim`
  - System packages: `libgl1-mesa-glx`, `libglib2.0-0`, `build-essential`
  - Python package runner: `uv`
  - WSGI Server: `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4`
- **`docker-compose.yml`**:
  - Services: `db` (Postgres 16), `redis` (Redis 7), `web` (Django Gunicorn), `nginx` (Nginx 1.25)
- **`nginx/nginx.conf`**:
  - Upstream `web:8000`
  - Wildcard domain server block `server_name *.ourapp.com ourapp.com;`
  - Static files alias `/app/staticfiles/`
