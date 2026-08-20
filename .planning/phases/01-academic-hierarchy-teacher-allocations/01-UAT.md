---
status: testing
phase: 01-academic-hierarchy-teacher-allocations
source:
  - .planning/phases/01-academic-hierarchy-teacher-allocations/01-01-SUMMARY.md
  - .planning/phases/01-academic-hierarchy-teacher-allocations/01-02-SUMMARY.md
started: 2026-08-20T17:52:00Z
updated: 2026-08-20T18:02:15Z
---

## Current Test

number: 7
name: Multi-Tenant Role Security Guard
expected: |
  Attempting to access `/academics/` as a Platform Super Admin or Faculty user results in HTTP 403 Forbidden, protecting academic master data at the tenant boundary.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Start Django dev server or run system checks. The application boots cleanly with 0 database or migration errors, and the full test suite passes.
result: pass

### 2. Admin Navigation & Academic Hub UI
expected: Log in as School Admin. The top navbar shows 'Academics'. Clicking it navigates to `/academics/` displaying the Apple-style segmented tabs (Academic Years, Standards & Divisions, Subjects, Teacher Allocations) with active session indicator.
result: pass

### 3. Academic Year Session Creation & Active Toggle
expected: Click '+ New Academic Year', enter name (e.g. '2026-2027'), date range, and set active. The table reflects the new year with a green '★ Active Current Session' badge.
result: pass

### 4. Grade Standards & Divisions Management
expected: Under 'Standards & Divisions' tab, add a Standard (e.g. 'Standard 10' with sort order). Click '+ Add Division' to add Section 'A' and 'B'. Standard card displays sort index badge and division pills with edit/delete controls.
result: pass

### 5. Curriculum Subjects Configuration
expected: Under 'Subjects' tab, click '+ Add Subject', provide name 'Mathematics' and code 'math-10'. Subject is created with auto-uppercase code 'MATH-10' and category badge ('Core Subject').
result: pass

### 6. Teacher Allocations Matrix & Multi-Teacher Co-Teaching
expected: Under 'Teacher Allocations' tab, select the active academic session. The matrix displays Standard 10 - Division A. Assign a Class Teacher and multiple Subject Teachers/Co-Teachers (e.g. 2 teachers for Mathematics). Assigned faculty names appear with individual delete badges and '+ Add Co-Teacher' triggers.
result: pass

### 7. Multi-Tenant Role Security Guard
expected: Attempting to access `/academics/` as a Platform Super Admin or Faculty user results in HTTP 403 Forbidden, protecting academic master data at the tenant boundary.
result: pending

## Summary

total: 7
passed: 6
issues: 0
pending: 1
skipped: 0

## Gaps

[none yet]
