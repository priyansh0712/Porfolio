from django.urls import path

from apps.accounts import views
from apps.accounts import views_superadmin

app_name = 'accounts'

urlpatterns = [
    path('login/', views.TenantLoginView.as_view(), name='login'),
    path('logout/', views.TenantLogoutView.as_view(), name='logout'),
    path('dashboard/', views.TenantDashboardView.as_view(), name='dashboard'),
    path('superadmin/', views_superadmin.SuperAdminDashboardView.as_view(), name='superadmin_dashboard'),
]
