from django.urls import path
from apps.notes import views

app_name = 'notes'

urlpatterns = [
    path('upload/', views.SubjectFacultyNoteUploadView.as_view(), name='upload'),
    path('my-uploads/', views.FacultyMyNotesListView.as_view(), name='my_uploads'),
    path('review/', views.ClassTeacherNoteReviewView.as_view(), name='review'),
    path('student/', views.StudentPortalNotesView.as_view(), name='student_notes'),
]
