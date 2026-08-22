from django.contrib import admin
from django.urls import path, include

from django.http import HttpResponse

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('favicon.ico', lambda request: HttpResponse(status=204)),
    path('admin/', admin.site.urls),
    path('', include('apps.public.urls', namespace='public')),
    path('', include('apps.accounts.urls', namespace='accounts')),
    path('faculty/', include('apps.faculty.urls', namespace='faculty')),
    path('faculty/', include('apps.biometrics.urls', namespace='biometrics')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('', include('apps.schedules.urls', namespace='schedules')),
    path('', include('apps.reports.urls', namespace='reports')),
    path('leaves/', include('apps.leaves.urls', namespace='leaves')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('academics/', include('apps.academics.urls', namespace='academics')),
    path('students/', include('apps.students.urls', namespace='students')),
    path('onboarding/', include('apps.onboarding.urls', namespace='onboarding')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
