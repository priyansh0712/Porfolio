"""
Timetable Views — School Admin Weekly Schedule Management & Student Timetable View.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.academics.models import (
    AcademicYear, Division, Subject, ClassTimetable,
)
from apps.academics.services import AcademicService
from apps.faculty.models import Faculty
from apps.students.views import StudentRequiredMixin


class AdminTimetableManageView(SchoolAdminRequiredMixin, TemplateView):
    """
    GET: School Admin selects Division and views weekly timetable grid (Days 1-6 x Periods 1-8).
    POST: Admin adds or updates a period timetable slot for the selected division.
    """
    template_name = 'academics/admin_timetable_manage.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)

        divisions = Division.objects.filter(school=tenant, is_active=True).select_related('standard')
        ctx['divisions'] = divisions

        selected_div_id = self.request.GET.get('division_id')
        selected_division = None
        if selected_div_id:
            selected_division = divisions.filter(pk=selected_div_id).first()
        if not selected_division and divisions.exists():
            selected_division = divisions.first()

        ctx['selected_division'] = selected_division
        ctx['academic_year'] = current_year

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
            ctx['subjects'] = Subject.objects.filter(school=tenant, is_active=True)
            ctx['faculties'] = Faculty.objects.filter(school=tenant, is_active=True)
            ctx['days'] = ClassTimetable.DayOfWeek.choices
            ctx['periods'] = list(range(1, 9))

        return ctx

    def post(self, request):
        tenant = request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)

        div_id = request.POST.get('division_id')
        division = get_object_or_404(Division, pk=div_id, school=tenant)

        day_of_week = int(request.POST.get('day_of_week'))
        period_number = int(request.POST.get('period_number'))
        subject_id = request.POST.get('subject_id')
        faculty_id = request.POST.get('faculty_id')
        start_time = request.POST.get('start_time') or None
        end_time = request.POST.get('end_time') or None

        if not subject_id:
            ClassTimetable.objects.filter(
                school=tenant,
                academic_year=current_year,
                division=division,
                day_of_week=day_of_week,
                period_number=period_number,
            ).delete()
            messages.info(request, f"Period {period_number} cleared.")
        else:
            subject = get_object_or_404(Subject, pk=subject_id, school=tenant)
            faculty = Faculty.objects.filter(pk=faculty_id, school=tenant).first() if faculty_id else None

            ClassTimetable.objects.update_or_create(
                school=tenant,
                academic_year=current_year,
                division=division,
                day_of_week=day_of_week,
                period_number=period_number,
                defaults={
                    'subject': subject,
                    'faculty': faculty,
                    'start_time': start_time,
                    'end_time': end_time,
                }
            )
            messages.success(request, f"Period {period_number} updated for {division.standard.name} - {division.name}.")

        return redirect(f"/academics/timetable/manage/?division_id={division.pk}")


class StudentPortalTimetableView(StudentRequiredMixin, TemplateView):
    """
    GET: Logged-in student views weekly class timetable grid and today's schedule.
    """
    template_name = 'academics/student_portal_timetable.html'

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
