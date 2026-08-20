from django.contrib import admin
from django.urls import path, include

from django.http import HttpResponse

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
]
