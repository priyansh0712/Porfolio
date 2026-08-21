# Phase 3 Context: 4-Step Bulk Excel/CSV Onboarding Engine

## Overview
Phase 3 delivers a complete 4-step sequential bulk onboarding engine (`/onboarding/wizard/`) enabling School Admins to effortlessly import Faculty, Classes & Class Teachers, Subject Teacher Allocations, and Student Rosters using `.xlsx` Excel and `.csv` files with instant validation previews and atomic database commits.

---

## Locked Implementation Decisions

### 1. Stepper Wizard Interface (`/onboarding/wizard/`)
- **Route**: `/onboarding/wizard/` (accessible to School Admin via `SchoolAdminRequiredMixin`).
- **UI Architecture**: Apple Design System Stepper Header with 4 sequential steps:
  - **Step 1: Faculty Roster** (`BULK-02`): Uploads teachers list, checks duplicate emails/employee codes, creates User accounts (`default_password='Admin@123'`).
  - **Step 2: Classes & Class Teachers** (`BULK-03`): Creates Standards, Divisions, and assigns Class Teachers (validates teacher exists and is unassigned).
  - **Step 3: Subject Teacher Mappings** (`BULK-04`): Creates Subjects and Subject Teacher allocations with dependency checks on existing classes and teachers.
  - **Step 4: Student Roster** (`BULK-05`): Uploads student roster, checks GR Number uniqueness, links to Standard+Division, auto-creates Student User accounts (`username` = GR No, default password = `Admin@123`).

### 2. Validation & Preview Engine (`apps.onboarding.services.BulkImportService`)
- Parses `.xlsx` (via `openpyxl`) and `.csv` files in RAM without disk persistence.
- Performs multi-tenant scoped validation against current school database:
  - Standard/Division existence & dependency checks.
  - Duplicate email, employee code, GR Number, and roll number checks.
- Generates interactive validation preview table displaying row index, data fields, status badge (`VALID` green / `ERROR` red), and exact error descriptions.
- Atomic commit (`@transaction.atomic`): Only valid rows are saved upon user clicking "Confirm & Import".

### 3. Sample Download Generator (`/onboarding/sample/<step>/<fmt>/`)
- Endpoint serving `.xlsx` and `.csv` sample files pre-formatted with exact column headers, header styling, and realistic dummy sample rows for all 4 stages.

---

## Requirements Traceability
- **BULK-01**: Downloadable sample Excel (`.xlsx`) and CSV (`.csv`) templates with instructions and dummy sample rows for all 4 import stages.
- **BULK-02**: Step 1 Faculty Bulk Import with duplicate checks, preview badges, and User account creation.
- **BULK-03**: Step 2 Class & Class Teacher Bulk Import with validation preview and atomic commit.
- **BULK-04**: Step 3 Subject Teacher Mapping Bulk Import with dependency checks.
- **BULK-05**: Step 4 Student Bulk Import with GR Number uniqueness checks, student User creation, preview table, and atomic commit.
