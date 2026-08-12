from django.urls import path

from apps.biometrics import views

app_name = 'biometrics'

urlpatterns = [
    path(
        '<int:pk>/enroll-face/',
        views.FacultyFaceEnrollView.as_view(),
        name='enroll_face',
    ),
    path(
        '<int:pk>/reset-face/',
        views.FacultyFaceResetView.as_view(),
        name='reset_face',
    ),
]
