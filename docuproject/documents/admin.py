# documents/admin.py

from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner','uploaded_at', 'is_favorite', 'department')
    list_filter = ( 'uploaded_at', 'is_favorite', 'department')
    search_fields = ('title', 'owner__email', 'file__name')
    readonly_fields = ('uploaded_at',)

    fieldsets = (
        (None, {
            'fields': ('title', 'owner', 'file', 'department')
        }),
        ('Metadata', {
            'fields': ('is_favorite', 'shared_with', 'uploaded_at'),
        }),
    )