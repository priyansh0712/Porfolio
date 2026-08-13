# Phase 9 Context: Admin Dashboard, Reports & Audit Log

## Overview
Phase 9 delivers the School Admin Dashboard (`/dashboard/`), Date-wise & Faculty-wise Attendance Reporting Suite (`/reports/`), CSV export, and an immutable manual attendance correction audit engine (`AttendanceCorrection`).

---

## Locked Implementation Decisions

### 1. School Admin Dashboard (`/dashboard/`)
- **Route**: `/dashboard/` extending `SchoolAdminRequiredMixin`.
- **Layout**: Apple Design System layout with 5 KPI summary cards:
  - Total Faculty
  - Present Today
  - Late Today
  - Absent Today (Faculty with no scan today)
  - Total Scans Today
- **Today's Live Activity Feed**: Apple Data Table displaying today's check-ins/outs with status badges, timestamps, and quick action drawer.

### 2. Manual Attendance Correction & Audit Log (`apps.reports.models`)
- **Model**: `AttendanceCorrection` storing:
  - `school`: ForeignKey to `tenants.School` (CASCADE)
  - `attendance`: ForeignKey to `attendance.AttendanceLog` (CASCADE)
  - `performed_by`: ForeignKey to `accounts.User` (SET_NULL, null=True)
  - `old_status`: CharField
  - `new_status`: CharField
  - `old_check_in_time`: DateTimeField (null=True)
  - `new_check_in_time`: DateTimeField (null=True)
  - `old_check_out_time`: DateTimeField (null=True)
  - `new_check_out_time`: DateTimeField (null=True)
  - `reason`: CharField (max_length=255, mandatory)
  - `created_at`: DateTimeField (auto_now_add=True)
- **UI**: Correction modal on attendance log row requiring a mandatory reason string. Audit trail viewer tab/drawer showing correction history per record.

### 3. Attendance Reports & CSV Export (`/reports/`)
- **Route**: `/reports/` extending `SchoolAdminRequiredMixin`.
- **Filters**: Date Range (Start Date – End Date), Department, Status (`PRESENT`, `LATE`, `HALF_DAY`).
- **Export**: `GET /reports/export/csv/` generating downloadable CSV file formatted with headers: `Date`, `Employee Code`, `Faculty Name`, `Department`, `Check In`, `Check Out`, `Duration`, `Status`, `Early Departure`.

---

## Requirements Traceability
- **RPT-01**: School Admin attendance dashboard showing daily summaries, faculty history views, and date-wise punctuality metrics.
- **AUDIT-01**: Immutable correction audit trail capturing admin ID, timestamp, original values, new values, and mandatory reason string.
