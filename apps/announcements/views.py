"""
Announcements Views — School Admin Broadcast Management & Student/Faculty Visibility.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.announcements.forms import SchoolAnnouncementForm
from apps.announcements.models import SchoolAnnouncement
from apps.announcements.services import AnnouncementService
from apps.students.views import StudentRequiredMixin


class SchoolAdminAnnouncementManageView(SchoolAdminRequiredMixin, TemplateView):
    """
    GET: School Admin / Principal views all broadcast notices & creation form.
    POST: School Admin creates a new targeted notice and dispatches in-app notifications.
    """
    template_name = 'announcements/admin_announcements.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        announcements = SchoolAnnouncement.objects.filter(
            school=tenant,
        ).select_related('author').order_by('-published_at')

        ctx['announcements'] = announcements
        ctx['form'] = SchoolAnnouncementForm()
        return ctx

    def post(self, request):
        tenant = request.tenant
        form = SchoolAnnouncementForm(request.POST)

        if form.is_valid():
            title = form.cleaned_data['title']
            content = form.cleaned_data['content']
            target_audience = form.cleaned_data['target_audience']
            is_active = form.cleaned_data['is_active']

            announcement = AnnouncementService.broadcast_notice(
                school=tenant,
                author=request.user,
                title=title,
                content=content,
                target_audience=target_audience,
                is_active=is_active,
            )

            messages.success(
                request,
                f"Principal Notice '{announcement.title}' published and delivered to {announcement.get_target_audience_display()}!"
            )
            return redirect('announcements:manage')
        else:
            messages.error(request, 'Failed to publish notice. Please check form errors.')
            ctx = self.get_context_data()
            ctx['form'] = form
            return self.render_to_response(ctx)


class AnnouncementDeleteView(SchoolAdminRequiredMixin, View):
    """POST: Delete an announcement."""

    def post(self, request, pk):
        tenant = request.tenant
        announcement = get_object_or_404(SchoolAnnouncement, pk=pk, school=tenant)
        title = announcement.title
        announcement.delete()
        messages.success(request, f"Notice '{title}' deleted.")
        return redirect('announcements:manage')


class AcknowledgeAnnouncementView(LoginRequiredMixin, View):
    """
    POST: Dismisses / acknowledges a one-time popup notice for the current user.
    """
    def post(self, request, pk):
        tenant = getattr(request, 'tenant', None)
        announcement = get_object_or_404(SchoolAnnouncement, pk=pk, school=tenant)

        AnnouncementService.acknowledge_notice(
            school=tenant,
            announcement=announcement,
            user=request.user,
        )

        return JsonResponse({'status': 'ok', 'message': 'Notice acknowledged successfully.'})


class StudentAnnouncementListView(StudentRequiredMixin, TemplateView):
    """
    GET: Logged-in student views broadcast announcements targeted to ALL or STUDENTS.
    """
    template_name = 'announcements/student_announcements.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        announcements = SchoolAnnouncement.objects.filter(
            school=tenant,
            is_active=True,
            target_audience__in=[
                SchoolAnnouncement.TargetAudience.ALL,
                SchoolAnnouncement.TargetAudience.STUDENTS,
            ],
        ).select_related('author').order_by('-published_at')

        ctx['announcements'] = announcements
        return ctx


class FacultyAnnouncementListView(LoginRequiredMixin, TemplateView):
    """
    GET: Logged-in faculty views broadcast notices targeted to ALL or FACULTY.
    """
    template_name = 'announcements/student_announcements.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in [User.Role.FACULTY, User.Role.SCHOOL_ADMIN]:
            raise PermissionDenied("Only faculty members can access faculty notices.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        announcements = SchoolAnnouncement.objects.filter(
            school=tenant,
            is_active=True,
            target_audience__in=[
                SchoolAnnouncement.TargetAudience.ALL,
                SchoolAnnouncement.TargetAudience.FACULTY,
            ],
        ).select_related('author').order_by('-published_at')

        ctx['announcements'] = announcements
        ctx['is_faculty_view'] = True
        return ctx
