# Quick Task Plan: Fix UI review findings for Phase 4

**Task ID:** 260825-dyc  
**Date:** 2026-08-25  
**Goal:** Address and fix the visual audit findings identified in `04-UI-REVIEW.md` across Phase 4 templates and components.

---

### Key Tasks:

1. **Refactor Color Tokens & Focus Rings (Remove `#5A2132` / `#481A28`)**:
   - `templates/faculty/my_class.html`: Replace `#5A2132` with Apple Action Blue (`#0066cc`) / Apple Ink (`#1d1d1f`).
   - `templates/faculty/my_subjects.html`: Replace `#5A2132` with Apple Action Blue (`#0066cc`).
   - `templates/accounts/password_change.html`: Replace `#5A2132` focus rings with `#0066cc`.
   - `templates/students/partials/modals.html`: Replace `#5A2132` / `#481A28` focus rings and buttons with `#0066cc` / `#0071e3`, and remove hardcoded inline `Plus Jakarta Sans` font declarations.

2. **Fix Navigation Headers & Mobile Drawer Integration**:
   - `templates/components/navbar_faculty.html`: Fix mobile drawer `"My Class"` route from `students:hub` to `faculty:my_class`. Add `"My Subjects"` and `"Password & Security"` to mobile drawer. Replace raw `🔒 Password` emoji with SVG lock icon.
   - `templates/components/navbar_student.html`: Clean up `🔒 Password` emoji with SVG lock icon.

3. **Enhance Password Form UX**:
   - `templates/accounts/password_change.html`: Add password visibility toggles (eye icons) and balanced button styling.

4. **Verification**:
   - Run full unit test suite `python manage.py test` to ensure zero regressions (246/246 passing).
