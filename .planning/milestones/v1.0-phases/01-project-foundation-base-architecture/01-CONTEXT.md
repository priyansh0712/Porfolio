# Phase 1: Project Foundation & Base Architecture - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the core project foundation: initializing a Django 5.1 project with PostgreSQL database connectivity, setting up Tailwind CSS 3.4 compilation via npm CLI, structuring modular Django apps inside an `apps/` directory, implementing split environment settings (`django-environ`), and rendering a responsive base HTML template (`base.html`) with a Minimal White & Gray design theme.

</domain>

<decisions>
## Implementation Decisions

### Project Architecture & App Organization
- **D-01:** Use modular `apps/` folder structure (`apps.core`, `apps.tenants`, `apps.accounts`, `apps.public`, `apps.faculty`, `apps.biometrics`, `apps.schedules`, `apps.attendance`, `apps.reports`) to keep codebase clean and maintainable.

### Asset Pipeline & Styling
- **D-02:** Use official Tailwind CSS CLI via `package.json` scripts (`npm run watch:css`, `npm run build:css`) compiling `static/css/src/input.css` to `static/css/dist/styles.css`.
- **D-03:** Base HTML template (`templates/base.html`) styling uses a Minimal White & Gray design theme with subtle border dividers, clean typography, responsive navigation, flash message alerts container, and content blocks.

### Environment & Configuration
- **D-04:** Use split Django settings directory (`config/settings/base.py`, `config/settings/local.py`, `config/settings/production.py`) powered by `django-environ` reading variables from `.env`.

### Agent's Discretion
- Database connection configuration, standard middleware loading order, logging setup, and base template block naming (`title`, `content`, `extra_css`, `extra_js`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/PROJECT.md` — Core value, overall constraints, and architecture principles
- `.planning/REQUIREMENTS.md` — v1 requirements and scope boundaries
- `.planning/research/STACK.md` — Recommended technology stack and versions (Django 5.1, Python 3.12, PostgreSQL 16, Tailwind 3.4)
- `.planning/research/ARCHITECTURE.md` — Layered monolith project structure and data flow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Greenfield codebase — initial setup will establish foundation assets for subsequent phases.

### Established Patterns
- Split settings pattern (`config/settings/base.py`, `local.py`, `production.py`).
- Modular app structure inside `apps/`.

### Integration Points
- `manage.py` configured with `PYTHONPATH` or app discovery to support `apps.*` imports.
- `static/css/dist/styles.css` linked in `templates/base.html`.

</code_context>

<specifics>
## Specific Ideas

- Theme: Minimal White & Gray theme with subtle border dividers for a clean, professional SaaS look.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed strictly within Phase 1 foundation scope.

</deferred>

---

*Phase: 01-project-foundation-base-architecture*
*Context gathered: 2026-08-11*
