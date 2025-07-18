
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, IndividualProfile, CompanyProfile, EmployeeProfile

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'user_type', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('User Type', {'fields': ('user_type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('User Type', {'fields': ('user_type',)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(IndividualProfile)
admin.site.register(CompanyProfile)
admin.site.register(EmployeeProfile)
