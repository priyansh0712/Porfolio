"""
URL Configuration for apps.academics.
"""
from django.urls import path
from apps.academics import views

app_name = 'academics'

urlpatterns = [
    # Main Hub
    path('', views.AcademicHubView.as_view(), name='hub'),

    # Academic Year CRUD
    path('years/create/', views.AcademicYearCreateView.as_view(), name='year_create'),
    path('years/<int:pk>/edit/', views.AcademicYearUpdateView.as_view(), name='year_edit'),
    path('years/<int:pk>/set-current/', views.AcademicYearSetCurrentView.as_view(), name='year_set_current'),
    path('years/<int:pk>/delete/', views.AcademicYearDeleteView.as_view(), name='year_delete'),

    # Standards CRUD
    path('standards/create/', views.StandardCreateView.as_view(), name='standard_create'),
    path('standards/<int:pk>/edit/', views.StandardUpdateView.as_view(), name='standard_edit'),
    path('standards/<int:pk>/delete/', views.StandardDeleteView.as_view(), name='standard_delete'),

    # Divisions CRUD
    path('divisions/create/', views.DivisionCreateView.as_view(), name='division_create'),
    path('divisions/<int:pk>/edit/', views.DivisionUpdateView.as_view(), name='division_edit'),
    path('divisions/<int:pk>/delete/', views.DivisionDeleteView.as_view(), name='division_delete'),

    # Subjects CRUD
    path('subjects/create/', views.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<int:pk>/edit/', views.SubjectUpdateView.as_view(), name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),

    # Allocations
    path('allocations/class-teacher/', views.ClassTeacherAssignView.as_view(), name='assign_class_teacher'),
    path('allocations/subject-teacher/', views.SubjectTeacherAssignView.as_view(), name='assign_subject_teacher'),
    path('allocations/<int:pk>/edit-subject-teacher/', views.SubjectTeacherUpdateView.as_view(), name='edit_subject_teacher'),
    path('allocations/<int:pk>/delete-subject-teacher/', views.SubjectTeacherDeleteView.as_view(), name='delete_subject_teacher'),
]
