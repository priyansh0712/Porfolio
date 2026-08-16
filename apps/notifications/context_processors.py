from apps.notifications.models import InAppNotification


def unread_notifications_count(request):
    """
    Exposes the unread notification count for the authenticated user
    within the current school tenant context.
    """
    if request.user.is_authenticated:
        # Resolve count based on current tenant context
        tenant = getattr(request, 'tenant', None)
        if tenant:
            count = InAppNotification.objects.filter(
                school=tenant,
                user=request.user,
                is_read=False
            ).count()
        else:
            count = InAppNotification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
