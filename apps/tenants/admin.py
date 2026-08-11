from django.contrib import admin
from .models import School

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'subdomain', 'contact_email', 'is_active', 'created_at')
    search_fields = ('name', 'subdomain', 'contact_email')
    list_filter = ('is_active', 'created_at')
    prepopulated_fields = {'subdomain': ('name',)}
