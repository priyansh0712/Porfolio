# Phase 1: Project Foundation & Base Architecture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 01-project-foundation-base-architecture
**Areas discussed:** Django App Structure, Tailwind CSS Setup Strategy, Environment & Settings Config, Base HTML Template Layout & Styling Tokens

---

## Django App Structure & Directory Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Modular `apps/` folder architecture | Group all Django apps inside `apps/` (apps.tenants, apps.accounts, etc.) | ✓ |
| Flat root directory apps | Place apps directly at project root | |
| Agent discretion | Let agent choose | |

**User's choice:** (Recommended) Modular apps/ folder architecture (apps/tenants, apps/accounts, etc.)

---

## Tailwind CSS Setup Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Tailwind CLI via npm package.json script | Direct watcher & full control via npm scripts | ✓ |
| django-tailwind package | Managed via Django manage.py command | |
| Agent discretion | Let agent choose | |

**User's choice:** (Recommended) Tailwind CLI via npm package.json script (Direct watcher & full control)

---

## Environment & Settings Config

| Option | Description | Selected |
|--------|-------------|----------|
| Split settings with django-environ & .env | base.py, local.py, production.py powered by django-environ | ✓ |
| Single config/settings.py file | Single settings file with python-dotenv | |
| Agent discretion | Let agent choose | |

**User's choice:** (Recommended) Split settings (base.py, local.py, production.py) with django-environ & .env

---

## Base HTML Template Layout & Styling Tokens

| Option | Description | Selected |
|--------|-------------|----------|
| Modern Slate & Indigo theme | Deep slate/indigo header with responsive navbar | |
| Minimal White & Gray theme | Clean white/gray design with subtle borders | ✓ |
| Agent discretion | Let agent choose | |

**User's choice:** Minimal White & Gray theme with subtle borders

---

## Agent's Discretion

- Database connection settings, middleware ordering, logging format, and base template block names.

## Deferred Ideas

None — discussion stayed within phase scope.
