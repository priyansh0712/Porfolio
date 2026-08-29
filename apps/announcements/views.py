"""
Announcements Views — School Admin Broadcast Management & Student Visibility.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.announcements.forms import SchoolAnnouncementForm
from apps.announcements.models import SchoolAnnouncement
from apps.students.views import StudentRequiredMixin


class SchoolAdminAnnouncementManageView(SchoolAdminRequiredMixin, TemplateView):
    """
    GET: School Admin views all announcements & creation form.
    POST: School Admin creates a new broadcast announcement.
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
            announcement = form.save(commit=False)
            announcement.school = tenant
            announcement.author = request.user
            announcement.save()

            messages.success(request, f"Announcement '{announcement.title}' published successfully!")
            return redirect('announcements:manage')
        else:
            messages.error(request, 'Failed to publish announcement. Please check form errors.')
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
        messages.success(request, f"Announcement '{title}' deleted.")
        return redirect('announcements:manage')


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
            target_audience__in=[SchoolAnnouncement.TargetAudience.ALL, SchoolAnnouncement.TargetAudience.STUDENTS],
        ).select_related('author').order_by('-published_at')

        ctx['announcements'] = announcements
        return ctx
