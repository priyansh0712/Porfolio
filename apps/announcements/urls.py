from django.urls import path
from apps.announcements import views

app_name = 'announcements'

urlpatterns = [
    path('manage/', views.SchoolAdminAnnouncementManageView.as_view(), name='manage'),
    path('<int:pk>/delete/', views.AnnouncementDeleteView.as_view(), name='delete'),
    path('student/', views.StudentAnnouncementListView.as_view(), name='student_list'),
]
