"""
Timetable Views — School Admin & Class Teacher Weekly Schedule Management & Student Timetable View.
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.academics.models import (
    AcademicYear, Division, Subject, ClassTimetable, ClassTeacherAllocation,
)
from apps.academics.services import AcademicService
from apps.academics.services_timetable import TimetableService, TimetableExcelService
from apps.faculty.models import Faculty
from apps.students.views import StudentRequiredMixin
from apps.tenants.features import FeatureService


class TimetableManagePermissionMixin:
    """
    Ensures the user is either a School Admin or an assigned Class Teacher for the current tenant.
    Also ensures the 'timetable' feature flag is active for the school.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        tenant = request.tenant
        if not FeatureService.is_enabled(tenant, 'timetable'):
            raise PermissionDenied("The Timetable feature is disabled for this school institute.")

        # Allow Super Admin & School Admin
        if request.user.role in [User.Role.SUPER_ADMIN, User.Role.SCHOOL_ADMIN]:
            return super().dispatch(request, *args, **kwargs)

        # Allow Faculty only if they are an active Class Teacher
        if request.user.role == User.Role.FACULTY:
            current_year = AcademicService.get_current_academic_year(tenant)
            is_class_teacher = ClassTeacherAllocation.objects.filter(
                school=tenant,
                academic_year=current_year,
                faculty__user=request.user,
            ).exists()
            if is_class_teacher:
                return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied("You do not have permission to manage class timetables.")


class AdminTimetableManageView(TimetableManagePermissionMixin, TemplateView):
    """
    GET: Authorized Admin / Class Teacher selects Division and views weekly timetable grid.
    POST: Admin / Class Teacher adds, updates, or clears a period timetable slot.
    """
    template_name = 'academics/admin_timetable_manage.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)

        # Retrieve only divisions the user is authorized to manage
        divisions = TimetableService.get_manageable_divisions(self.request.user, tenant, current_year)
        ctx['divisions'] = divisions

        selected_div_id = self.request.GET.get('division_id')
        selected_division = None
        if selected_div_id:
            selected_division = divisions.filter(pk=selected_div_id).first()
        if not selected_division and divisions.exists():
            selected_division = divisions.first()

        ctx['selected_division'] = selected_division
        ctx['academic_year'] = current_year
        ctx['is_class_teacher'] = (self.request.user.role == User.Role.FACULTY)

        if selected_division and current_year:
            slots = ClassTimetable.objects.filter(
                school=tenant,
                academic_year=current_year,
                division=selected_division,
            ).select_related('subject', 'faculty')

            grid = {day: {} for day in range(1, 7)}
            for slot in slots:
                grid[slot.day_of_week][slot.period_number] = slot

            ctx['grid'] = grid
            ctx['subjects'] = Subject.objects.filter(school=tenant, is_active=True).order_by('name')
            ctx['faculties'] = Faculty.objects.filter(school=tenant, is_active=True).order_by('first_name', 'last_name')
            ctx['days'] = ClassTimetable.DayOfWeek.choices
            ctx['periods'] = list(range(1, 9))

        return ctx

    def post(self, request):
        tenant = request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)

        div_id = request.POST.get('division_id')
        division = get_object_or_404(Division, pk=div_id, school=tenant)

        # Verify authorization for this specific division
        if not TimetableService.can_manage_division_timetable(request.user, division, current_year):
            raise PermissionDenied("You do not have authorization to modify the timetable for this class.")

        day_of_week = int(request.POST.get('day_of_week'))
        period_number = int(request.POST.get('period_number'))
        subject_id = request.POST.get('subject_id')
        faculty_id = request.POST.get('faculty_id')
        start_time_raw = request.POST.get('start_time')
        end_time_raw = request.POST.get('end_time')

        if not subject_id:
            # Clear slot
            deleted_count, _ = ClassTimetable.objects.filter(
                school=tenant,
                academic_year=current_year,
                division=division,
                day_of_week=day_of_week,
                period_number=period_number,
            ).delete()
            if deleted_count:
                messages.info(request, f"Period {period_number} cleared for {division.standard.name} - {division.name}.")
            else:
                messages.info(request, f"Period {period_number} is already empty.")
        else:
            subject = get_object_or_404(Subject, pk=subject_id, school=tenant)
            faculty = Faculty.objects.filter(pk=faculty_id, school=tenant, is_active=True).first() if faculty_id else None

            start_t = TimetableService.parse_time_str(start_time_raw)
            end_t = TimetableService.parse_time_str(end_time_raw)

            # Conflict Validation
            conflicts = TimetableService.validate_slot_conflicts(
                school=tenant,
                academic_year=current_year,
                division=division,
                day_of_week=day_of_week,
                period_number=period_number,
                faculty=faculty,
                start_time=start_t,
                end_time=end_t,
            )

            if conflicts:
                for err in conflicts:
                    messages.error(request, f"Conflict Error: {err}")
                return redirect(f"/academics/timetable/manage/?division_id={division.pk}")

            ClassTimetable.objects.update_or_create(
                school=tenant,
                academic_year=current_year,
                division=division,
                day_of_week=day_of_week,
                period_number=period_number,
                defaults={
                    'subject': subject,
                    'faculty': faculty,
                    'start_time': start_t,
                    'end_time': end_t,
                }
            )
            messages.success(
                request,
                f"Period {period_number} successfully saved for {division.standard.name} - {division.name} ({subject.name})."
            )

        return redirect(f"/academics/timetable/manage/?division_id={division.pk}")


class TimetableTemplateDownloadView(TimetableManagePermissionMixin, View):
    """
    Streams downloadable sample Timetable Excel template (.xlsx).
    """
    def get(self, request):
        tenant = request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)
        excel_bytes = TimetableExcelService.generate_sample_template(tenant, current_year)

        response = HttpResponse(
            excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response['Content-Disposition'] = 'attachment; filename="timetable_upload_template.xlsx"'
        return response


class TimetableExcelUploadView(TimetableManagePermissionMixin, View):
    """
    POST: Processes bulk timetable Excel file upload and reports validation results.
    """
    def post(self, request):
        tenant = request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)

        uploaded_file = request.FILES.get('excel_file')
        if not uploaded_file:
            messages.error(request, "Please select an Excel file (.xlsx or .xls) to upload.")
            return redirect('academics:timetable_manage')

        result = TimetableExcelService.import_timetable_excel(
            school=tenant,
            academic_year=current_year,
            file_obj=uploaded_file,
            user=request.user,
        )

        if result['errors']:
            if result['successful'] > 0:
                messages.warning(
                    request,
                    f"Import completed with warnings: {result['successful']} periods saved, {result['failed']} failed out of {result['total_processed']} rows."
                )
            else:
                messages.error(
                    request,
                    f"Excel import failed ({result['failed']} errors out of {result['total_processed']} rows). Please review errors below."
                )
            for err in result['errors'][:8]:  # Show top 8 error items in alert banner
                messages.error(request, f"• {err}")
            if len(result['errors']) > 8:
                messages.error(request, f"...and {len(result['errors']) - 8} more errors.")
        else:
            messages.success(
                request,
                f"Excel import successful! All {result['successful']} timetable period slots were created/updated across classes."
            )

        return redirect('academics:timetable_manage')


class StudentPortalTimetableView(StudentRequiredMixin, TemplateView):
    """
    GET: Logged-in student views weekly class timetable grid and today's schedule for their own class.
    """
    template_name = 'academics/student_portal_timetable.html'

    def dispatch(self, request, *args, **kwargs):
        tenant = request.tenant
        if not FeatureService.is_enabled(tenant, 'timetable'):
            raise PermissionDenied("The Timetable feature is disabled for this school.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        student = getattr(self.request.user, 'student_profile', None)
        ctx['student'] = student

        if student and student.division:
            current_year = AcademicService.get_current_academic_year(tenant)
            slots = ClassTimetable.objects.filter(
                school=tenant,
                academic_year=current_year,
                division=student.division,
            ).select_related('subject', 'faculty').order_by('day_of_week', 'period_number')

            grid = {day: {} for day in range(1, 7)}
            for slot in slots:
                grid[slot.day_of_week][slot.period_number] = slot

            ctx['grid'] = grid
            ctx['days'] = ClassTimetable.DayOfWeek.choices
            ctx['periods'] = list(range(1, 9))

            today_weekday = timezone.localdate().isoweekday()
            ctx['today_weekday'] = today_weekday if today_weekday <= 6 else 1
            ctx['today_slots'] = [grid[today_weekday].get(p) for p in range(1, 9) if grid.get(today_weekday, {}).get(p)]

        return ctx
