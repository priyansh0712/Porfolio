from django.urls import path
from apps.fees import views

app_name = 'fees'

urlpatterns = [
    # School Admin Routes
    path('', views.AdminFeeDashboardView.as_view(), name='dashboard'),
    path('categories/', views.FeeCategoryListView.as_view(), name='categories'),
    path('structures/', views.FeeStructureListView.as_view(), name='structures'),
    path('students/', views.StudentFeeRosterView.as_view(), name='student_roster'),
    path('students/<int:pk>/', views.StudentFeeDetailView.as_view(), name='student_detail'),
    path('collect/', views.FeePaymentCollectView.as_view(), name='collect_payment'),
    path('receipts/<int:pk>/', views.FeeReceiptDetailView.as_view(), name='receipt_detail'),
    path('reports/', views.FeeReportsView.as_view(), name='reports'),

    # Student Portal Route
    path('my-fees/', views.StudentFeePortalView.as_view(), name='student_fees'),
]
