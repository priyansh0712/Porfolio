from django.urls import path
from .views import LandingPageView, SchoolRegistrationView, RegistrationSuccessView

app_name = 'public'

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing'),
    path('register/', SchoolRegistrationView.as_view(), name='register'),
    path('register/success/', RegistrationSuccessView.as_view(), name='register_success'),
]
