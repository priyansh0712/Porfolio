from django.urls import path
from apps.students import views

app_name = 'students'

urlpatterns = [
    # Student Hub (list + tabs)
    path('', views.StudentHubView.as_view(), name='hub'),

    # Student CRUD
    path('add/', views.StudentCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.StudentUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.StudentDeleteView.as_view(), name='delete'),
    path('<int:pk>/restore/', views.StudentRestoreView.as_view(), name='restore'),
    path('<int:pk>/hard-delete/', views.StudentHardDeleteView.as_view(), name='hard_delete'),
    path('bulk-deactivate/', views.StudentBulkDeactivateView.as_view(), name='bulk_deactivate'),
    path('bulk-delete/', views.StudentBulkDeleteView.as_view(), name='bulk_delete'),
    path('bulk-restore/', views.StudentBulkRestoreView.as_view(), name='bulk_restore'),

    # Transfer request workflow
    path('<int:pk>/transfer/', views.TransferRequestCreateView.as_view(), name='transfer_create'),
    path('transfers/<int:pk>/approve/', views.TransferApproveView.as_view(), name='transfer_approve'),
    path('transfers/<int:pk>/reject/', views.TransferRejectView.as_view(), name='transfer_reject'),

    # AJAX
    path('api/divisions/', views.DivisionsForStandardView.as_view(), name='api_divisions'),

    # Student portal (for logged-in students)
    path('portal/', views.StudentPortalView.as_view(), name='portal'),

    # Dynamic Custom Fields & Field Config (School Admin)
    path('custom-fields/add/', views.CustomFieldCreateView.as_view(), name='custom_field_create'),
    path('custom-fields/<int:pk>/edit/', views.CustomFieldUpdateView.as_view(), name='custom_field_update'),
    path('custom-fields/<int:pk>/toggle/', views.CustomFieldToggleView.as_view(), name='custom_field_toggle'),
    path('custom-fields/<int:pk>/delete/', views.CustomFieldDeleteView.as_view(), name='custom_field_delete'),
    path('form-config/', views.StudentFormFieldConfigUpdateView.as_view(), name='form_config_update'),
]
