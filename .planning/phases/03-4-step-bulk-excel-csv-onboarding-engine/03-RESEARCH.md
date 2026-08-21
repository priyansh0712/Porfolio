# Phase 3 Research: 4-Step Bulk Excel/CSV Onboarding Engine

## Executive Summary
Phase 3 implements the 4-step bulk onboarding suite allowing School Admins to populate Faculty, Classes, Subject Mappings, and Students using Excel (`.xlsx`) and CSV (`.csv`) files. This research documents template structure, parsing algorithms, validation rules, user creation defaults, and preview data structures.

---

## 1. 4-Step Import Pipeline Specifications

### Step 1: Faculty Bulk Import (`BULK-02`)
- **Headers**: `First Name`, `Last Name`, `Email`, `Employee Code`, `Department`, `Designation`
- **Validation**:
  - `First Name`, `Last Name`, `Email`, `Employee Code` required.
  - Email format validation.
  - Unique `email` and `employee_code` per school tenant.
- **Commit Actions**:
  - Creates `Faculty` record linked to school tenant.
  - Creates identity-only `User` record (`email=email`, `username=email`, `role='FACULTY'`, `password='Admin@123'`).

### Step 2: Classes & Class Teachers Bulk Import (`BULK-03`)
- **Headers**: `Standard Name`, `Standard Code`, `Division Name`, `Class Teacher Employee Code`
- **Validation**:
  - `Standard Name` and `Division Name` required.
  - Standard gets created or looked up by `name`/`code` for active academic year.
  - Division gets created or looked up for standard.
  - If `Class Teacher Employee Code` is provided, validates that faculty exists in school tenant and is not already assigned as Class Teacher in current academic year.
- **Commit Actions**:
  - Creates `Standard` and `Division`.
  - Creates `ClassTeacherAllocation` record.

### Step 3: Subject Teacher Mappings Bulk Import (`BULK-04`)
- **Headers**: `Standard Name`, `Division Name`, `Subject Name`, `Subject Code`, `Subject Teacher Employee Code`
- **Validation**:
  - `Standard Name`, `Division Name`, `Subject Name`, `Subject Teacher Employee Code` required.
  - Standard + Division combination must exist in tenant for current academic year.
  - Subject created or looked up by name/code.
  - Subject Teacher employee code must exist in tenant.
- **Commit Actions**:
  - Creates `Subject`.
  - Creates `SubjectTeacherAllocation`.

### Step 4: Student Roster Bulk Import (`BULK-05`)
- **Headers**: `GR Number`, `First Name`, `Last Name`, `Standard Name`, `Division Name`, `Roll Number`, `Gender`, `Date of Birth`, `Parent Phone`, `Parent Email`
- **Validation**:
  - `GR Number`, `First Name`, `Last Name`, `Standard Name`, `Division Name` required.
  - `GR Number` must be unique across school tenant (`Student.objects.filter(school=school, gr_number=gr)`).
  - Standard + Division combination must exist.
  - Roll number unique within Standard + Division.
- **Commit Actions**:
  - Creates `Student` record (`is_active=True`).
  - Creates `User` account (`username=gr_number`, `role='STUDENT'`, `password='Admin@123'`).

---

## 2. File Parsing & Sample Download Architecture

- **`openpyxl` Integration**: Parses uploaded `.xlsx` files using `openpyxl.load_workbook(file_obj, data_only=True)`.
- **`csv` Module Integration**: Parses uploaded `.csv` files using `csv.reader` with encoding fallback (`utf-8-sig`, `latin-1`).
- **Sample Files Generator**: Serves `.xlsx` files styled with bold header row and fill colors, as well as clean `.csv` files.
