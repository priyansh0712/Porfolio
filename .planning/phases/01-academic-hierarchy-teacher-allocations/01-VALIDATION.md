---
phase: 01
slug: academic-hierarchy-teacher-allocations
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-20
---

# Phase 01 — Validation Strategy (Academic Hierarchy & Teacher Allocations)

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|---|---|
| **Framework** | Django TestCase (`django.test.TestCase`) |
| **Config file** | `config/settings/base.py` |
| **Quick run command** | `python manage.py test apps.academics` |
| **Full suite command** | `python manage.py test` |
| **Estimated runtime** | ~5 seconds (app), ~20 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `python manage.py test apps.academics`
- **After every plan wave:** Run `python manage.py test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|---|---|---|---|
| 01-01-01 | 01 | 1 | ACAD-01, ACAD-02, ACAD-03, ACAD-04 | T-01-01 | Multi-tenant isolation at DB model level | unit | `python manage.py test apps.academics.tests.AcademicModelTests` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | ALLOC-01, ALLOC-02, ALLOC-03 | T-01-02 | Constraint integrity on teacher allocations | unit | `python manage.py test apps.academics.tests.AllocationModelTests` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | ACAD-01, ACAD-02, ACAD-03, ACAD-04 | T-01-03 | View & Form tenant authorization (SchoolAdmin only) | integration | `python manage.py test apps.academics.tests.AcademicViewTests` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | ALLOC-01, ALLOC-02, ALLOC-03 | T-01-04 | Class & Subject Teacher allocation workflow | integration | `python manage.py test apps.academics.tests.AllocationViewTests` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/academics/tests.py` — Test scaffolding covering multi-tenant isolation, unique constraints, active session switching, and role permission guards.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| Apple Design System visual audit | UI-Contract | Visual alignment verification | Navigate to `/academics/`, check `#f5f5f7` canvas, white cards, hairline borders, SF Pro typography, and segmented pill tabs. |
| Modal interaction UX | UI-Contract | Verify popup transitions and close handlers | Click "+ Add Division" inside a Standard card, verify modal opens and submits without page scroll displacement. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-20
