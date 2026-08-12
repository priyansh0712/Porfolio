from django.urls import path

from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.TenantLoginView.as_view(), name='login'),
    path('logout/', views.TenantLogoutView.as_view(), name='logout'),
    path('dashboard/', views.TenantDashboardView.as_view(), name='dashboard'),
]
