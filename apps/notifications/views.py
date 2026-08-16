from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.shortcuts import get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages

from apps.notifications.models import InAppNotification


class NotificationListView(LoginRequiredMixin, TemplateView):
    """
    Renders a paginated list of all in-app notifications for the logged-in user,
    scoped strictly to the school tenant context.
    """
    template_name = 'notifications/notification_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Query user notifications scoped to tenant
        notifications = InAppNotification.objects.filter(
            school=self.request.tenant,
            user=self.request.user
        ).order_by('-created_at')

        # Pagination: 20 per page
        paginator = Paginator(notifications, 20)
        page_number = self.request.GET.get('page')
        context['page_obj'] = paginator.get_page(page_number)
        
        return context


class MarkNotificationReadView(LoginRequiredMixin, View):
    """
    POST-only endpoint to mark a single notification as read.
    """
    def post(self, request, pk, *args, **kwargs):
        notif = get_object_or_404(
            InAppNotification,
            school=request.tenant,
            user=request.user,
            pk=pk
        )
        notif.is_read = True
        notif.save()
        
        messages.success(request, "Notification marked as read.")
        return redirect(request.GET.get('next', 'notifications:notification_list'))


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """
    POST-only endpoint to mark all notifications as read for the user.
    """
    def post(self, request, *args, **kwargs):
        InAppNotification.objects.filter(
            school=request.tenant,
            user=request.user,
            is_read=False
        ).update(is_read=True)
        
        messages.success(request, "All notifications marked as read.")
        return redirect('notifications:notification_list')
