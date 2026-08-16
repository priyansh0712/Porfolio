from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta

from apps.leaves.models import LeaveRequest
from apps.attendance.models import AttendanceLog


@receiver(post_save, sender=LeaveRequest)
def sync_attendance_logs_on_leave_request_save(sender, instance, **kwargs):
    """
    Automated attendance log generation / synchronization handler.
    
    1. If a leave request is APPROVED, writes/updates AttendanceLog entries
       with LEAVE status for each calendar date in the request span.
    2. If a request transitions to PENDING, REJECTED, or CANCELLED, deletes
       any auto-generated LEAVE logs within that date range.
    """
    if instance.status == LeaveRequest.Status.APPROVED:
        from django.utils import timezone
        current_date = instance.from_date
        while current_date <= instance.to_date:
            AttendanceLog.objects.update_or_create(
                school=instance.school,
                faculty=instance.faculty,
                date=current_date,
                defaults={
                    'status': AttendanceLog.Status.LEAVE,
                    'check_in_time': None,
                    'check_out_time': None,
                    'last_scan_at': timezone.now(),
                }
            )
            current_date += timedelta(days=1)
            
    elif instance.status in [LeaveRequest.Status.PENDING, LeaveRequest.Status.REJECTED, LeaveRequest.Status.CANCELLED]:
        # Delete any LEAVE attendance logs that match the date range and faculty
        AttendanceLog.objects.filter(
            school=instance.school,
            faculty=instance.faculty,
            date__range=(instance.from_date, instance.to_date),
            status=AttendanceLog.Status.LEAVE
        ).delete()
