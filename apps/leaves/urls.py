from django.urls import path
from apps.leaves import views

app_name = 'leaves'

urlpatterns = [
    path('allocation/upload/', views.LeaveAllocationUploadView.as_view(), name='upload_allocation'),
    path('allocation/template/', views.DownloadLeaveTemplateView.as_view(), name='download_template'),
    path('dashboard/', views.FacultyDashboardView.as_view(), name='faculty_dashboard'),
    path('apply/', views.ApplyLeaveView.as_view(), name='apply_leave'),
    path('admin/requests/', views.AdminLeaveRequestsView.as_view(), name='admin_requests'),
    path('requests/<int:pk>/approve/', views.ApproveLeaveRequestView.as_view(), name='approve_request'),
    path('requests/<int:pk>/reject/', views.RejectLeaveRequestView.as_view(), name='reject_request'),
    path('my-attendance/', views.FacultyAttendanceHistoryView.as_view(), name='faculty_attendance'),
]
