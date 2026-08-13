# Phase 9 Research: Admin Dashboard, Reports & Audit Log

## Executive Summary
Phase 9 implements the primary School Admin Dashboard (`/dashboard/`), Date-wise & Faculty-wise Attendance Reporting Suite (`/reports/`), CSV report exporter (`/reports/export/csv/`), and the immutable manual attendance correction audit engine (`AttendanceCorrection`). This research documents query optimization for daily metrics, CSV streaming architecture, and audit trail data structures.

---

## 1. Dashboard Metrics Aggregation Engine

### Required KPI Metrics (`apps.reports.services.DashboardService`)
1. **Total Active Faculty**: `Faculty.objects.filter(school=school, is_active=True).count()`
2. **Present Today**: `AttendanceLog.objects.filter(school=school, date=today, status='PRESENT').count()`
3. **Late Today**: `AttendanceLog.objects.filter(school=school, date=today, status='LATE').count()`
4. **Half-Day Today**: `AttendanceLog.objects.filter(school=school, date=today, status='HALF_DAY').count()`
5. **Absent Today**: Total active faculty minus distinct faculty IDs scanned today:
   $$\text{Absent Count} = \text{Total Active Faculty} - |\text{Set of Faculty IDs with scan today}|$$
6. **Live Feed**: `AttendanceLog.objects.filter(school=school, date=today).select_related('faculty').order_by('-last_scan_at')[:20]`

---

## 2. Attendance Correction Audit Engine

### Data Model (`apps.reports.models.AttendanceCorrection`)

```python
class AttendanceCorrection(TenantModel):
    attendance = models.ForeignKey('attendance.AttendanceLog', on_delete=models.CASCADE, related_name='corrections')
    performed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='performed_corrections')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    old_check_in_time = models.DateTimeField(null=True, blank=True)
    new_check_in_time = models.DateTimeField(null=True, blank=True)
    old_check_out_time = models.DateTimeField(null=True, blank=True)
    new_check_out_time = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, help_text='Mandatory explanation for audit trail')
```

### Atomic Correction Service (`ReportService.correct_attendance`)
- Wrapped in `@transaction.atomic`.
- Validates mandatory non-empty `reason` string.
- Creates `AttendanceCorrection` audit record recording before/after values and admin `performed_by`.
- Updates target `AttendanceLog` record.

---

## 3. CSV Export Architecture

- **Endpoint**: `/reports/export/csv/`
- **Content-Type**: `text/csv`
- **Headers**: `Date`, `Employee Code`, `Faculty Name`, `Department`, `Check In`, `Check Out`, `Duration (Hours)`, `Status`, `Early Departure`, `Corrections Count`.
- Uses Python `csv.writer` streaming response for low memory overhead.
