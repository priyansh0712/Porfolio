"""
Schedules App URL Configuration.

Routes:
  - /settings/schedule/ → ScheduleSettingsView (Admin schedule & holiday settings)
"""
from django.urls import path

from apps.schedules.views import ScheduleSettingsView

app_name = 'schedules'

urlpatterns = [
    path('settings/schedule/', ScheduleSettingsView.as_view(), name='settings'),
]
