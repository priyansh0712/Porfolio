from django.urls import path

from apps.onboarding import views

app_name = 'onboarding'

urlpatterns = [
    path('wizard/', views.OnboardingWizardView.as_view(), name='wizard'),
    path('sample/<int:step>/<str:fmt>/', views.SampleTemplateDownloadView.as_view(), name='sample-download'),
    path('api/validate/', views.OnboardingValidateAPIView.as_view(), name='api-validate'),
    path('api/commit/', views.OnboardingCommitAPIView.as_view(), name='api-commit'),
]
