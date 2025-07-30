
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


def get_user_storage_limit_mb(user):
    from packages.models import UserPackage  # to avoid circular import

    try:
        user_package = UserPackage.objects.get(user=user, is_active=True)
        return int(user_package.package.storage_limit_gb * 1024)
    except UserPackage.DoesNotExist:
        return 0  # No active package → no storage



class Department(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, limit_choices_to={'user_type': 'company'})

    def __str__(self):
        return f"{self.name} ({self.company.companyprofile.company_name})"

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('employee', 'Employee'),
    )

    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)

    def save(self, *args, **kwargs):
        self.username = self.email  # Auto-set username to email
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"
    @property
    def display_name(self):
        if self.user_type == 'individual':
            return self.individualprofile.full_name
        elif self.user_type == 'company':
            return self.companyprofile.admin_full_name
        elif self.user_type == 'employee':
            return self.employeeprofile.full_name
        return self.email

class IndividualProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return self.full_name

class CompanyProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    company_email = models.EmailField()
    company_phone = models.CharField(max_length=20)
    company_website = models.URLField(blank=True, null=True)  # ✅ New
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)  # ✅ New
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    admin_full_name = models.CharField(max_length=100)
    admin_phone = models.CharField(max_length=20)
    industry = models.CharField(max_length=100, blank=True, null=True)  # ✅ New
    number_of_employees = models.PositiveIntegerField(blank=True, null=True)  # ✅ New
    department = models.ForeignKey('accounts.Department', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.company_name
 

class EmployeeProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    company = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='employees')
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    gender = models.CharField(max_length=10, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    employee_code = models.CharField(max_length=50, blank=True)
    department = models.ForeignKey(Department,on_delete=models.SET_NULL,null=True,blank=True)
    join_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.full_name} ({self.department})"
