from django.urls import path
from apps.announcements import views

app_name = 'announcements'

urlpatterns = [
    path('manage/', views.SchoolAdminAnnouncementManageView.as_view(), name='manage'),
    path('<int:pk>/delete/', views.AnnouncementDeleteView.as_view(), name='delete'),
    path('acknowledge/<int:pk>/', views.AcknowledgeAnnouncementView.as_view(), name='acknowledge'),
    path('student/', views.StudentAnnouncementListView.as_view(), name='student_list'),
    path('faculty/', views.FacultyAnnouncementListView.as_view(), name='faculty_list'),
]
