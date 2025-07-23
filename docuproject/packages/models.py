from django.db import models
from django.conf import settings
from django.utils import timezone
from . import decorators

class Package(models.Model):
    USER_TYPES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]

    SUPPORT_LEVELS = [
        ('none', 'No Support'),
        ('basic', 'Basic Support'),
        ('priority', 'Priority Support'),
    ]

    SHARING_LEVELS = [
        ('none', 'No Sharing'),
        ('read_only', 'Limited Sharing'),
        ('secure', 'Advanced Sharing'),
    ]

    name = models.CharField(max_length=100)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    description = models.TextField(blank=True)

    # Core Features
    storage_limit_gb = models.FloatField()
    max_upload_mb = models.FloatField(default=10.0)
    support_level = models.CharField(max_length=20, choices=SUPPORT_LEVELS, default='none')
    sharing_level = models.CharField(max_length=20, choices=SHARING_LEVELS, default='none')
    retention_enabled = models.BooleanField(default=False)  # Archive/restore for documents
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)  

    # Company-Only
    max_employees = models.IntegerField(null=True, blank=True)
    max_departments = models.IntegerField(null=True, blank=True)
    analytics_level = models.CharField(max_length=20, choices=[('none', 'None'), ('basic', 'Basic'), ('advanced', 'Advanced')], default='none')
    versioning_enabled = models.BooleanField(default=False)
    audit_logs_enabled = models.BooleanField(default=False)

    # Pricing Info
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.user_type})"

class UserPackage(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def is_expired(self):
        return timezone.now().date() > self.end_date

    def days_left(self):
        return max((self.end_date - timezone.now().date()).days, 0)

    def __str__(self):
        return f"{self.user.email} - {self.package.name}"


class PackageFeature(models.Model):
    package = models.ForeignKey('Package', on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.package.name} - {self.name}"
