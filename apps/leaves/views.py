from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.contrib import messages
from django.core.exceptions import ValidationError

from apps.accounts.permissions import SchoolAdminRequiredMixin, FeatureRequiredMixin
from apps.leaves.services import LeaveAllocationService


class DownloadLeaveTemplateView(FeatureRequiredMixin, SchoolAdminRequiredMixin, View):
    """
    School Admin dynamic download of the pre-populated leave allocation template.
    """
    feature_key = 'faculty_leave'

    def get(self, request, *args, **kwargs):
        excel_data = LeaveAllocationService.generate_excel_template(request.tenant)
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="leave_allocation_template.xlsx"'
        return response


class LeaveAllocationUploadView(FeatureRequiredMixin, SchoolAdminRequiredMixin, View):
    """
    School Admin view to upload and preview leave allocations with row-level validation.
    """
    feature_key = 'faculty_leave'
    template_name = 'leaves/upload.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            messages.error(request, "Please select an Excel file to upload.")
            return render(request, self.template_name)

        filename = uploaded_file.name.lower()
        if not filename.endswith('.xlsx'):
            messages.error(request, "Unsupported file format. Please upload a valid Excel (.xlsx) file.")
            return render(request, self.template_name)

        try:
            success_count = LeaveAllocationService.import_leave_allocations(
                request.tenant,
                uploaded_file
            )
            context = {
                'success_message': f"Successfully updated leave allocations for {success_count} faculty members.",
                'success_count': success_count,
            }
            messages.success(request, context['success_message'])
            return render(request, self.template_name, context)

        except ValidationError as ve:
            # Check if validation error holds a list of individual row-level errors
            if hasattr(ve, 'messages'):
                row_errors = ve.messages
            else:
                row_errors = [str(ve)]

            context = {
                'row_errors': row_errors,
                'error_message': "The import failed because the file contains validation errors. Please review and correct the errors below.",
            }
            return render(request, self.template_name, context)
        except Exception as e:
            context = {
                'error_message': f"An unexpected error occurred while parsing the file: {str(e)}"
            }
            return render(request, self.template_name, context)


from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.utils import timezone
from apps.accounts.permissions import FacultyRequiredMixin
from apps.attendance.models import AttendanceLog
from apps.leaves.models import LeaveAllocation, LeaveRequest, LeaveType
from apps.leaves.forms import LeaveRequestForm


class FacultyDashboardView(FeatureRequiredMixin, FacultyRequiredMixin, TemplateView):
    """
    Renders the personal Faculty Dashboard showing attendance, leave balances,
    recent leave requests, and in-app notifications.
    """
    feature_key = 'faculty_leave'
    template_name = 'leaves/faculty_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faculty = self.request.user.faculty_profile
        today = timezone.localdate()

        # 1. Today's Attendance status
        today_log = AttendanceLog.objects.filter(
            school=self.request.tenant,
            faculty=faculty,
            date=today
        ).first()
        context['today_log'] = today_log

        # 2. Leave Balance tracking
        balances = []
        for l_type, l_name in LeaveType.choices:
            # Allocated days
            alloc = LeaveAllocation.objects.filter(
                school=self.request.tenant,
                faculty=faculty,
                leave_type=l_type
            ).first()
            allocated = alloc.allocated if alloc else 0

            # Sum of used days (approved request duration with schedule adjustments)
            approved = LeaveRequest.objects.filter(
                school=self.request.tenant,
                faculty=faculty,
                leave_type=l_type,
                status=LeaveRequest.Status.APPROVED
            )
            used = sum(r.used_days for r in approved)
            remaining = allocated - used

            balances.append({
                'type': l_type,
                'name': l_name,
                'allocated': allocated,
                'used': used,
                'remaining': remaining,
            })

        context['balances'] = balances

        # 3. Recent Leave Requests (past 15 entries)
        context['recent_requests'] = LeaveRequest.objects.filter(
            school=self.request.tenant,
            faculty=faculty
        ).order_by('-from_date', '-created_at')[:15]

        # 4. Recent Notifications (past 15 entries)
        context['notifications'] = self.request.user.notifications.all()[:15]

        # 5. Dynamic 30-Day Attendance Heatmap for logged-in Faculty
        start_date = today - timedelta(days=29)
        from apps.schedules.models import HolidayException, WorkingSchedule

        logs_by_date = {
            log.date: log
            for log in AttendanceLog.objects.filter(
                school=self.request.tenant,
                faculty=faculty,
                date__range=(start_date, today)
            )
        }

        # Fetch School Admin configured holidays
        school_holidays = {
            h.date: h.description
            for h in HolidayException.objects.filter(
                school=self.request.tenant,
                date__range=(start_date, today)
            )
        }
        for rh in HolidayException.objects.filter(school=self.request.tenant, is_recurring_yearly=True):
            for i in range(30):
                d = start_date + timedelta(days=i)
                if d.month == rh.date.month and d.day == rh.date.day:
                    school_holidays[d] = rh.description

        # Fetch non-working days from WorkingSchedule (default: ONLY Sunday 6 is weekend)
        off_days = set()
        schedules = WorkingSchedule.objects.filter(school=self.request.tenant)
        if schedules.exists():
            for ws in schedules:
                if not ws.is_working_day:
                    off_days.add(ws.day_of_week)
        else:
            off_days.add(6)  # Default: Only Sunday is weekend

        heatmap_days = []
        for i in range(30):
            d = start_date + timedelta(days=i)
            log = logs_by_date.get(d)
            is_holiday = d in school_holidays

            if log:
                if log.status == AttendanceLog.Status.PRESENT:
                    status_type = 'PRESENT'
                    status_label = 'Present (On-Time)'
                elif log.status == AttendanceLog.Status.LATE:
                    status_type = 'LATE'
                    status_label = 'Late Arrival'
                elif log.status == AttendanceLog.Status.HALF_DAY:
                    status_type = 'HALF_DAY'
                    status_label = 'Half Day'
                elif log.status == AttendanceLog.Status.LEAVE:
                    status_type = 'LEAVE'
                    status_label = 'Approved Leave'
                else:
                    status_type = 'ABSENT'
                    status_label = log.get_status_display()
            elif is_holiday:
                status_type = 'HOLIDAY'
                status_label = f"Holiday ({school_holidays[d]})"
            elif d.weekday() in off_days or (not schedules.exists() and d.weekday() == 6):
                status_type = 'WEEKEND'
                status_label = 'Sunday (Weekend)' if d.weekday() == 6 else 'Weekend Off'
            elif d < today:
                # Past working day with no scan = BOLD RED ABSENT
                status_type = 'ABSENT'
                status_label = 'Absent (Unrecorded)'
            else:
                # Today or future day with no scan
                status_type = 'PENDING'
                status_label = 'Pending Scan'

            heatmap_days.append({
                'day_number': d.day,
                'date_str': d.strftime('%b %d, %Y'),
                'status_type': status_type,
                'status_label': status_label,
            })

        context['heatmap_days'] = heatmap_days

        return context


class ApplyLeaveView(FeatureRequiredMixin, FacultyRequiredMixin, View):
    """
    Handles Faculty leave requests submission and validations.
    """
    feature_key = 'faculty_leave'
    template_name = 'leaves/apply_leave.html'

    def get(self, request, *args, **kwargs):
        form = LeaveRequestForm(
            faculty=request.user.faculty_profile,
            school=request.tenant
        )
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        faculty = request.user.faculty_profile
        form = LeaveRequestForm(
            request.POST,
            faculty=faculty,
            school=request.tenant
        )
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.school = request.tenant
            leave_request.faculty = faculty
            leave_request.status = LeaveRequest.Status.PENDING
            leave_request.save()
            messages.success(request, "Your leave request has been submitted successfully.")
            return redirect('accounts:dashboard')

        return render(request, self.template_name, {'form': form})


from django.shortcuts import get_object_or_404
from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.notifications.models import InAppNotification
from apps.faculty.models import Faculty


class AdminLeaveRequestsView(FeatureRequiredMixin, SchoolAdminRequiredMixin, TemplateView):
    """
    Renders the leave request review dashboard for School Admins.
    Supports filtering by status, faculty member, and date range.
    """
    feature_key = 'faculty_leave'
    template_name = 'leaves/admin_requests.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.tenant

        # Base queryset
        requests = LeaveRequest.objects.filter(school=school)

        # Apply optional filters
        status = self.request.GET.get('status', '').strip()
        faculty_id = self.request.GET.get('faculty', '').strip()
        from_date_str = self.request.GET.get('from_date', '').strip()
        to_date_str = self.request.GET.get('to_date', '').strip()

        if status:
            requests = requests.filter(status=status)
        if faculty_id:
            requests = requests.filter(faculty_id=faculty_id)
        if from_date_str:
            requests = requests.filter(from_date__gte=from_date_str)
        if to_date_str:
            requests = requests.filter(to_date__lte=to_date_str)

        # Order newest first
        context['leave_requests'] = requests.order_by('-created_at', '-from_date')

        # Active faculties list for filter dropdown
        context['faculties'] = Faculty.objects.filter(
            school=school,
            is_active=True
        ).order_by('first_name', 'last_name')

        # Pass back filter state
        context['selected_status'] = status
        context['selected_faculty'] = int(faculty_id) if faculty_id.isdigit() else ''
        context['selected_from_date'] = from_date_str
        context['selected_to_date'] = to_date_str

        # Status choices
        context['status_choices'] = LeaveRequest.Status.choices

        return context


class ApproveLeaveRequestView(FeatureRequiredMixin, SchoolAdminRequiredMixin, View):
    """
    POST-only view to approve a pending leave request.
    """
    feature_key = 'faculty_leave'
    def post(self, request, pk, *args, **kwargs):
        req = get_object_or_404(LeaveRequest, pk=pk, school=request.tenant)
        if req.status != LeaveRequest.Status.PENDING:
            messages.error(request, "Only pending leave requests can be approved.")
            return redirect('leaves:admin_requests')

        req.status = LeaveRequest.Status.APPROVED
        req.save()

        # Create in-app notification
        InAppNotification.objects.create(
            school=request.tenant,
            user=req.faculty.user,
            title="Leave Request Approved",
            message=f"Your leave request for {req.from_date} to {req.to_date} has been approved."
        )

        messages.success(request, f"Leave request for {req.faculty.full_name} has been approved.")
        return redirect('leaves:admin_requests')


class RejectLeaveRequestView(FeatureRequiredMixin, SchoolAdminRequiredMixin, View):
    """
    POST-only view to reject a pending leave request with a mandatory explanation.
    """
    feature_key = 'faculty_leave'
    def post(self, request, pk, *args, **kwargs):
        req = get_object_or_404(LeaveRequest, pk=pk, school=request.tenant)
        if req.status != LeaveRequest.Status.PENDING:
            messages.error(request, "Only pending leave requests can be rejected.")
            return redirect('leaves:admin_requests')

        reason = request.POST.get('rejection_reason', '').strip()
        if not reason:
            messages.error(request, "A reason must be provided to reject a leave request.")
            return redirect('leaves:admin_requests')

        req.status = LeaveRequest.Status.REJECTED
        req.rejection_reason = reason
        req.save()

        # Create in-app notification
        InAppNotification.objects.create(
            school=request.tenant,
            user=req.faculty.user,
            title="Leave Request Rejected",
            message=f"Your leave request for {req.from_date} to {req.to_date} has been rejected. Reason: {reason}"
        )

        messages.success(request, f"Leave request for {req.faculty.full_name} has been rejected.")
        return redirect('leaves:admin_requests')


from django.core.paginator import Paginator
from datetime import datetime, timedelta

class FacultyAttendanceHistoryView(FacultyRequiredMixin, TemplateView):
    """
    Renders date-wise paginated history of check-in/out logs for Faculty,
    complete with summary statistics cards (Present, Late, Half Day, Leave, Absent).
    """
    template_name = 'leaves/faculty_attendance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faculty = self.request.user.faculty_profile
        today = timezone.localdate()

        # Date range & Month-wise query handling
        month_param = self.request.GET.get('month', '').strip()
        from_date_str = self.request.GET.get('from_date', '').strip()
        to_date_str = self.request.GET.get('to_date', '').strip()

        if month_param:
            try:
                m_date = datetime.strptime(month_param, '%Y-%m').date()
                from_date = m_date.replace(day=1)
                # Compute end of month
                if from_date.month == 12:
                    to_date = from_date.replace(year=from_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    to_date = from_date.replace(month=from_date.month + 1, day=1) - timedelta(days=1)
            except ValueError:
                from_date = today - timedelta(days=30)
                to_date = today
        elif from_date_str:
            try:
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            except ValueError:
                from_date = today - timedelta(days=30)
            if to_date_str:
                try:
                    to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
                except ValueError:
                    to_date = today
            else:
                to_date = today
        else:
            from_date = today - timedelta(days=30)
            to_date = today

        # Generate list of last 12 months for month selector dropdown
        available_months = []
        cur_m = today.replace(day=1)
        for _ in range(12):
            available_months.append({
                'value': cur_m.strftime('%Y-%m'),
                'label': cur_m.strftime('%B %Y')
            })
            # move to previous month
            if cur_m.month == 1:
                cur_m = cur_m.replace(year=cur_m.year - 1, month=12)
            else:
                cur_m = cur_m.replace(month=cur_m.month - 1)

        context['available_months'] = available_months
        context['selected_month'] = month_param or from_date.strftime('%Y-%m')

        # Base Attendance Logs queryset in date range
        logs = AttendanceLog.objects.filter(
            school=self.request.tenant,
            faculty=faculty,
            date__range=(from_date, to_date)
        )

        # 1. Summary statistics calculations
        present_count = logs.filter(status=AttendanceLog.Status.PRESENT).count()
        late_count = logs.filter(status=AttendanceLog.Status.LATE).count()
        half_day_count = logs.filter(status=AttendanceLog.Status.HALF_DAY).count()
        leave_count = logs.filter(status=AttendanceLog.Status.LEAVE).count()

        # Absent is calculated implicitly as working days with no scan record
        total_days = (to_date - from_date).days + 1
        absent_count = max(0, total_days - logs.count())

        context['present_count'] = present_count
        context['late_count'] = late_count
        context['half_day_count'] = half_day_count
        context['leave_count'] = leave_count
        context['absent_count'] = absent_count

        # Date boundaries for filter form
        context['from_date'] = from_date.strftime('%Y-%m-%d')
        context['to_date'] = to_date.strftime('%Y-%m-%d')

        # 2. Paginated Date-wise Logs
        paginator = Paginator(logs.order_by('-date'), 15)  # 15 logs per page
        page_number = self.request.GET.get('page')
        context['page_obj'] = paginator.get_page(page_number)

        return context
