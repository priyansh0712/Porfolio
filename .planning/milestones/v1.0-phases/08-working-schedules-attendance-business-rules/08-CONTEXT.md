# Phase 8 Context: Working Schedules & Attendance Business Rules

## Overview
Phase 8 implements tenant-scoped school working schedules, grace period thresholds, half-day calculation, holiday exceptions, and an Apple-aesthetic settings management page (`/settings/schedule/`).

---

## Locked Implementation Decisions

### 1. Working Schedule & Day-of-Week Configuration
- **Model**: `WorkingSchedule` storing `school` (FK), `day_of_week` (0=Mon .. 6=Sun), `is_working_day` (Boolean), `start_time` (TimeField), `end_time` (TimeField), `grace_period_minutes` (IntegerField, default 15).
- **Default Baseline**: Monday-Friday 08:00 to 16:00 (15 min grace); Saturday 08:00 to 12:00; Sunday non-working.

### 2. Punctuality Calculation Engine
- **Late Check-In**: Check-in time $> \text{start\_time} + \text{grace\_period\_minutes}$ (e.g. $> 08:15$) $\implies \text{status} = \text{LATE}$.
- **Half-Day**: Total duration $< 4$ hours OR check-in time $> 11:00$ AM $\implies \text{status} = \text{HALF\_DAY}$.
- **Early Departure**: Check-out time $< \text{end\_time} - \text{grace\_period\_minutes}$ (e.g. $< 15:45$) $\implies$ flag `early_departure = True`.

### 3. Holiday Exceptions
- **Model**: `HolidayException` storing `school` (FK), `date` (DateField), `description` (CharField), `is_recurring_yearly` (Boolean).
- **Behavior**: Scans on holiday dates are permitted without late penalties or absent tags.

### 4. Admin Schedule Settings UI
- **URL**: `/settings/schedule/` (Layer 2 `SchoolAdminRequiredMixin`).
- **Design**: Apple-aesthetic settings page with day-by-day tabbed forms, grace period sliders/inputs, and holiday exception table.

---

## Requirements Traceability
- **SCHED-01**: Configurable school working schedule engine with day-specific working hours and holiday exceptions.
- **SCHED-02**: Late threshold & grace period engine calculating Present, Late, Half-Day, and Early Departure automatically.
