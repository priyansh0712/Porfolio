"""
Reports & Dashboard Views — School Admin Dashboard, Reports, CSV Exporter, and Corrections (3-Layer Security).

Layer 1: TenantMiddleware (request.tenant)
Layer 2: SchoolAdminRequiredMixin (role-based access)
Layer 3: Queryset scoping (school=request.tenant)
"""
import logging
from datetime import datetime

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.attendance.models import AttendanceLog
from apps.faculty.models import Faculty
from apps.reports.services import DashboardService, ReportService

logger = logging.getLogger(__name__)


class AdminDashboardView(SchoolAdminRequiredMixin, TemplateView):
    """
    Renders the primary School Admin Dashboard (`/dashboard/`).

    Features:
      - 5 KPI summary cards (Total Faculty, Present Today, Late Today, Absent Today, Total Scans).
      - Today's Live Activity Feed table.
      - Quick actions sidebar (Kiosk link, Schedule settings, Add Faculty).
    """
    template_name = 'reports/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.tenant

        metrics = DashboardService.get_metrics(school)
        context.update(metrics)
        context['school'] = school
        return context


class AttendanceReportView(SchoolAdminRequiredMixin, TemplateView):
    """
    Renders the Date-wise & Faculty-wise Attendance Reports page (`/reports/`).

    Features:
      - Start Date / End Date range filter.
      - Department filter dropdown.
      - Status filter dropdown (PRESENT, LATE, HALF_DAY).
      - Search input (Faculty Name or Employee Code).
      - Pagination & CSV export action.
    """
    template_name = 'reports/attendance_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.tenant

        # Get query parameters
        start_date_str = self.request.GET.get('start_date', '')
        end_date_str = self.request.GET.get('end_date', '')
        department = self.request.GET.get('department', '')
        status = self.request.GET.get('status', '')
        search = self.request.GET.get('search', '')

        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        qs = ReportService.get_report_queryset(
            school=school,
            start_date=start_date,
            end_date=end_date,
            department=department,
            status=status,
            search=search,
        )

        departments = Faculty.objects.filter(school=school).values_list('department', flat=True).distinct()

        context.update({
            'attendance_logs': qs[:100],  # Top 100 results
            'total_count': qs.count(),
            'departments': [d for d in departments if d],
            'status_choices': AttendanceLog.Status.choices,
            'selected_start_date': start_date_str,
            'selected_end_date': end_date_str,
            'selected_department': department,
            'selected_status': status,
            'search_query': search,
        })
        return context


class AttendanceExportCSVView(SchoolAdminRequiredMixin, View):
    """
    GET endpoint for downloading attendance report data as a CSV file.
    """

    def get(self, request):
        school = request.tenant

        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')
        department = request.GET.get('department', '')
        status = request.GET.get('status', '')
        search = request.GET.get('search', '')

        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        qs = ReportService.get_report_queryset(
            school=school,
            start_date=start_date,
            end_date=end_date,
            department=department,
            status=status,
            search=search,
        )

        csv_content = ReportService.generate_csv(school, qs)

        filename = f"attendance_report_{school.subdomain}_{timezone.localdate()}.csv"
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class AttendanceCorrectView(SchoolAdminRequiredMixin, View):
    """
    POST-only endpoint for performing manual attendance corrections.
    """

    def post(self, request, pk):
        school = request.tenant
        attendance = get_object_or_404(AttendanceLog, pk=pk, school=school)

        new_status = request.POST.get('new_status')
        reason = request.POST.get('reason', '')

        if not new_status or new_status not in dict(AttendanceLog.Status.choices):
            messages.error(request, "Invalid attendance status selected.")
            return redirect('reports:report-list')

        try:
            ReportService.correct_attendance(
                school=school,
                admin_user=request.user,
                attendance=attendance,
                new_status=new_status,
                reason=reason,
            )
            messages.success(request, f"Attendance record for {attendance.faculty.full_name} updated.")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.exception("Error correcting attendance log %s", pk)
            messages.error(request, "An unexpected error occurred during correction.")

        return redirect('reports:report-list')
