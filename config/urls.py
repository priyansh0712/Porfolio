from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.public.urls', namespace='public')),
    path('', include('apps.accounts.urls', namespace='accounts')),
]
