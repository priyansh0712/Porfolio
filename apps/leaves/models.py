from django.db import models
from django.core.exceptions import ValidationError
from apps.tenants.models import TenantModel
from apps.faculty.models import Faculty


class LeaveType(models.TextChoices):
    CASUAL = 'CASUAL', 'Casual Leave'
    SICK = 'SICK', 'Sick Leave'
    PAID = 'PAID', 'Paid Leave'


class LeaveAllocation(TenantModel):
    """
    Tracks how many days of a specific leave type are allocated to a faculty member.
    Allocations are scoped to the school tenant.
    """
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='leave_allocations',
        help_text="Faculty member who owns this leave allocation."
    )
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.choices,
        help_text="Type of leave allocated (Casual, Sick, Paid)."
    )
    allocated = models.PositiveIntegerField(
        default=0,
        help_text="Number of allocated leave days."
    )

    class Meta:
        ordering = ['faculty', 'leave_type']
        verbose_name = 'Leave Allocation'
        verbose_name_plural = 'Leave Allocations'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'faculty', 'leave_type'],
                name='unique_faculty_leave_type_per_school'
            )
        ]

    def __str__(self):
        return f"{self.faculty.full_name} — {self.get_leave_type_display()}: {self.allocated}"


class LeaveRequest(TenantModel):
    """
    Represents a leave request submitted by a faculty member.
    Tracks status transitions (PENDING, APPROVED, REJECTED, CANCELLED) and auditable dates.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='leave_requests',
        help_text="Faculty member requesting leave."
    )
    leave_type = models.CharField(
        max_length=20,
        choices=LeaveType.choices,
        help_text="Leave category (Casual, Sick, Paid)."
    )
    from_date = models.DateField(
        help_text="Start date of leave (inclusive)."
    )
    to_date = models.DateField(
        help_text="End date of leave (inclusive)."
    )
    reason = models.TextField(
        blank=True,
        default='',
        help_text="Reason/description for the leave request."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current state of the request."
    )
    rejection_reason = models.TextField(
        blank=True,
        default='',
        help_text="Explanation reason if rejected by School Admin."
    )

    class Meta:
        ordering = ['-from_date', '-created_at']
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'

    def clean(self):
        super().clean()
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValidationError({
                'from_date': "From Date cannot be after To Date."
            })

    @property
    def used_days(self):
        """
        Calculates the net leave days requested, excluding non-working days
        (from WorkingSchedule) and designated school holidays (from HolidayException).
        """
        if not self.from_date or not self.to_date:
            return 0

        from datetime import timedelta
        from apps.schedules.models import WorkingSchedule, HolidayException
        from django.db.models import Q

        # Prefetch schedules and holidays
        schedules = {
            s.day_of_week: s.is_working_day 
            for s in WorkingSchedule.objects.filter(school=self.school)
        }
        
        holidays_qs = HolidayException.objects.filter(
            Q(school=self.school) & (
                Q(date__range=(self.from_date, self.to_date)) |
                Q(is_recurring_yearly=True)
            )
        )
        
        holiday_dates = set()
        recurring_days = set() # (month, day)
        for h in holidays_qs:
            if h.is_recurring_yearly:
                recurring_days.add((h.date.month, h.date.day))
            else:
                holiday_dates.add(h.date)

        count = 0
        current_date = self.from_date
        while current_date <= self.to_date:
            day_of_week = current_date.weekday()
            is_working = schedules.get(day_of_week, day_of_week < 5)
            
            if is_working:
                is_holiday = (
                    current_date in holiday_dates or 
                    (current_date.month, current_date.day) in recurring_days
                )
                if not is_holiday:
                    count += 1
            current_date += timedelta(days=1)
            
        return count

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.faculty.full_name} — {self.get_leave_type_display()} ({self.from_date} to {self.to_date})"
