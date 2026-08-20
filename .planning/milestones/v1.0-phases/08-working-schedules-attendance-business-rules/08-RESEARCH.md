# Phase 8 Research: Working Schedules & Attendance Business Rules

## Executive Summary
Phase 8 implements tenant-scoped working schedules, day-of-week working hours, grace period thresholds, punctuality status calculations (`PRESENT`, `LATE`, `HALF_DAY`, `EARLY_DEPARTURE`), holiday exceptions, and an Apple-aesthetic settings view (`/settings/schedule/`). This research details data modeling, punctuality engine integration into `AttendanceStateMachine`, default tenant initialization, and admin UI design.

---

## 1. Schedule Data Model & Relational Isolation

### Models (`apps.schedules.models`)

#### `WorkingSchedule`
- `school`: ForeignKey to `tenants.School` (CASCADE).
- `day_of_week`: IntegerField (0 = Monday, 6 = Sunday).
- `is_working_day`: BooleanField (default `True` for Mon-Fri, `True` for Sat, `False` for Sun).
- `start_time`: TimeField (default `08:00:00`).
- `end_time`: TimeField (default `16:00:00` for Mon-Fri, `12:00:00` for Sat).
- `grace_period_minutes`: PositiveIntegerField (default `15`).
- `Meta`: `unique_together = ('school', 'day_of_week')`.

#### `HolidayException`
- `school`: ForeignKey to `tenants.School` (CASCADE).
- `date`: DateField.
- `description`: CharField (max_length=255).
- `is_recurring_yearly`: BooleanField (default `False`).
- `Meta`: `unique_together = ('school', 'date')`.

---

## 2. Punctuality Calculation Engine

### Evaluation Pipeline (`PunctualityCalculator`)

When a face scan is processed by `AttendanceStateMachine`:

```mermaid
flowchart TD
    Scan[Face Scan Received] --> IsHoliday{Is Today a Holiday?}
    IsHoliday -- Yes --> MarkPresent[Status = PRESENT (No Penalty)]
    IsHoliday -- No --> CheckWorkingDay{Is Today a Working Day?}
    CheckWorkingDay -- No --> MarkPresent
    CheckWorkingDay -- Yes --> CheckInTime{Check-In > Start Time + Grace?}
    CheckInTime -- Yes --> MarkLate[Status = LATE]
    CheckInTime -- No --> CheckHalfDay{Check-In > 11:00 AM or Duration < 4h?}
    CheckHalfDay -- Yes --> MarkHalfDay[Status = HALF_DAY]
    CheckHalfDay -- No --> MarkPresent
```

### Formula Definitions
1. **Grace Window**: $\text{Late Cutoff} = \text{start\_time} + \text{timedelta(minutes=grace\_period\_minutes)}$.
2. **Late Arrival**: $\text{check\_in\_time.time()} > \text{Late Cutoff} \implies \text{status} = \text{LATE}$.
3. **Half-Day**: $\text{check\_in\_time.time()} > \text{11:00 AM}$ OR $\text{duration} < 4.0\text{ hours} \implies \text{status} = \text{HALF\_DAY}$.
4. **Early Departure**: $\text{check\_out\_time.time()} < (\text{end\_time} - \text{grace}) \implies \text{early\_departure = True}$.

---

## 3. Automatic Tenant Initializer

When a new school registers (Phase 2 `SchoolRegistrationService`), default `WorkingSchedule` records (Monday through Sunday) are automatically seeded for the tenant:
- **Monday – Friday**: Working Day, 08:00 AM – 04:00 PM, 15 min grace.
- **Saturday**: Working Day, 08:00 AM – 12:00 PM, 15 min grace.
- **Sunday**: Non-Working Day.

---

## 4. Admin Settings UI (`/settings/schedule/`)

- Built using Apple Design System (`border-gray-200`, `rounded-2xl`, `#0066cc` buttons).
- Tabbed interface for Day-of-Week hours (Monday through Sunday).
- Grace Period input field (minutes).
- Holiday Exception management table with inline addition modal.
