from django.urls import path

from apps.faculty import views

app_name = 'faculty'

urlpatterns = [
    path('', views.FacultyListView.as_view(), name='list'),
    path('create/', views.FacultyCreateView.as_view(), name='create'),
    path('bulk-import/', views.FacultyBulkImportView.as_view(), name='bulk_import'),
    path('sample-csv/', views.FacultySampleCSVView.as_view(), name='sample_csv'),
    path('<int:pk>/edit/', views.FacultyUpdateView.as_view(), name='edit'),
    path('<int:pk>/toggle-status/', views.FacultyToggleStatusView.as_view(), name='toggle_status'),
    path('<int:pk>/detail/', views.FacultyDetailAPIView.as_view(), name='detail_api'),
]
