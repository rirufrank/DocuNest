# documents/models.py

from django.db import models
from django.conf import settings
import os
from django.core.exceptions import ValidationError


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1][1:].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('Unsupported file extension.')

ALLOWED_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png',
    'xls', 'xlsx',
]


class Document(models.Model):
    # Ownership
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # File handling
    file = models.FileField(upload_to='documents/', validators=[validate_file_extension])
    size = models.BigIntegerField(null=True, blank=True)  # in bytes
    
    @property
    def size_in_mb(self):
        if self.size is None:
            return "0 MB"
        size_mb = self.size / (1024 * 1024)
        return f"{size_mb:.2f} MB"
    
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
    def get_icon_class(self):
        mapping = {
            'pdf': 'bi-file-earmark-pdf',
            'doc': 'bi-file-earmark-word',
            'docx': 'bi-file-earmark-word',
            'jpeg': 'bi-file-earmark-image',
            'jpg': 'bi-file-earmark-image',
            'png': 'bi-file-earmark-image',
            'xlsx': 'bi-file-earmark-excel',
            'xls': 'bi-file-earmark-excel',
            'ppt': 'bi-file-earmark-ppt',
            'pptx': 'bi-file-earmark-ppt',
            'mp3': 'bi-file-earmark-music',
            'wav': 'bi-file-earmark-music',
            'mp4': 'bi-file-earmark-play',
            'mkv': 'bi-file-earmark-play',
            'txt': 'bi-file-earmark-text',
        }
        return mapping.get(self.file_type, 'bi-file-earmark')  
    
    # Optional: Department (if tied to employee)
    department = models.CharField(max_length=100, blank=True, null= True)

    # For company admins to share with employees
    is_company_wide = models.BooleanField(default=False)
    
    # Optional: Public/Private toggle
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def file_extension(self):
        return self.file.name.split('.')[-1].lower()

    @property
    def file_type(self):
        return self.file_extension()

    def readable_file_size(self):
        # Convert bytes to KB/MB/GB
        size = self.size or 0
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def categorize_file_type(self):
        ext = self.file_extension()
        image_types = ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'ico')
        document_types = ('pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx')
        video_types = ('mp4', 'mkv', 'mov')
        audio_types = ('mp3', 'wav', 'ogg')

        if ext in image_types:
            return 'Image'
        elif ext in document_types:
            return 'Document'
        elif ext in video_types:
            return 'Video'
        elif ext in audio_types:
            return 'Audio'
        else:
            return 'Other'


    def save(self, *args, **kwargs):
        if self.file:
            self.size = self.file.size
        super().save(*args, **kwargs)
