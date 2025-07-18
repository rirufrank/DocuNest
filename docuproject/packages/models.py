from django.db import models
from django.conf import settings

class Package(models.Model):
    PACKAGE_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=PACKAGE_TYPE_CHOICES)
    storage_limit_mb = models.PositiveIntegerField()
    max_employees = models.PositiveIntegerField(null=True, blank=True)  # Only for companies
    can_share_documents = models.BooleanField(default=False)
    support_level = models.CharField(max_length=50, default='Basic')
    retention_period_days = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserPackage(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    activated_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.package.name}"

