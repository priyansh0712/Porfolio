from django.urls import path
from django.views.generic import RedirectView
from apps.fees import views

app_name = 'fees'

urlpatterns = [
    # School Admin Simplified Hub
    path('', views.AdminFeesHubView.as_view(), name='dashboard'),
    path('template/', views.FeeExcelTemplateDownloadView.as_view(), name='template_download'),
    path('upload/', views.FeeExcelUploadView.as_view(), name='excel_upload'),
    path('record-payment/', views.RecordPaymentView.as_view(), name='record_payment'),
    path('receipts/<int:pk>/', views.FeeReceiptDetailView.as_view(), name='receipt_detail'),

    # Student Portal Route
    path('my-fees/', views.StudentPortalFeesView.as_view(), name='student_fees'),

    # Backwards-compatible aliases to the unified hub
    path('categories/', RedirectView.as_view(pattern_name='fees:dashboard', permanent=False), name='categories'),
    path('structures/', RedirectView.as_view(pattern_name='fees:dashboard', permanent=False), name='structures'),
    path('students/', RedirectView.as_view(pattern_name='fees:dashboard', permanent=False), name='student_roster'),
    path('collect/', RedirectView.as_view(pattern_name='fees:dashboard', permanent=False), name='collect_payment'),
    path('reports/', RedirectView.as_view(pattern_name='fees:dashboard', permanent=False), name='reports'),
]
