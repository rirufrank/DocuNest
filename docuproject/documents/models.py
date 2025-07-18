# documents/models.py

from django.db import models
from django.conf import settings
import os

class Document(models.Model):
    # Ownership
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # File handling
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=50, blank=True)  # auto-filled
    size = models.BigIntegerField(null=True, blank=True)  # in bytes

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Flags & categories
    is_favorite = models.BooleanField(default=False)
    trashed = models.BooleanField(default=False)
    tags = models.CharField(max_length=255, blank=True)

    # Sharing
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='documents_shared_with_me',
        blank=True
    )

    # Optional: Department (if tied to employee)
    department = models.CharField(max_length=100, blank=True, null= True)

    # Optional: Public/Private toggle
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def file_extension(self):
        return os.path.splitext(self.file.name)[1].lower().replace(".", "")

    def readable_file_size(self):
        # Convert bytes to KB/MB/GB
        size = self.size or 0
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def save(self, *args, **kwargs):
        if self.file:
            self.size = self.file.size
            self.file_type = self.file_extension()
        super().save(*args, **kwargs)
