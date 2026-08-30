from apps.announcements.services import AnnouncementService


def pending_principal_notice(request):
    """
    Injects `pending_popup_notice` into the template context if the authenticated user
    has an active, unacknowledged Principal Notice in the current tenant context.
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        tenant = getattr(request, 'tenant', None)
        if tenant:
            notice = AnnouncementService.get_pending_popup_notice(request.user, tenant)
            return {'pending_popup_notice': notice}
    return {'pending_popup_notice': None}
