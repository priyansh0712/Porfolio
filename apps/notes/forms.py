from django import forms
from apps.notes.models import SubjectNote
from apps.notes.validators import validate_note_file_extension, validate_note_file_size


class SubjectNoteUploadForm(forms.ModelForm):
    class Meta:
        model = SubjectNote
        fields = ['division', 'subject', 'title', 'description', 'file']
        widgets = {
            'division': forms.Select(attrs={'class': 'w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0066cc]'}),
            'subject': forms.Select(attrs={'class': 'w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0066cc]'}),
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0066cc]', 'placeholder': 'e.g. Chapter 3: Algebra Notes'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0066cc]', 'rows': 3, 'placeholder': 'Optional brief notes or instructions for students...'}),
            'file': forms.FileInput(attrs={'class': 'w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0066cc]'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            validate_note_file_extension(file)
            validate_note_file_size(file)
        return file
