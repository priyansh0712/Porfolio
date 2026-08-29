from django import forms
from apps.announcements.models import SchoolAnnouncement


class SchoolAnnouncementForm(forms.ModelForm):
    class Meta:
        model = SchoolAnnouncement
        fields = ['title', 'content', 'target_audience', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0066cc]', 'placeholder': 'e.g. Annual Sports Day Announcement'}),
            'content': forms.Textarea(attrs={'class': 'w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0066cc]', 'rows': 4, 'placeholder': 'Write announcement message...'}),
            'target_audience': forms.Select(attrs={'class': 'w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0066cc]'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-[#0066cc] focus:ring-[#0066cc]'}),
        }
