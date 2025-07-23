from django.contrib import admin
from .models import Package, UserPackage, PackageFeature



@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_type', 'storage_limit_gb', 'price', )
    list_filter = ('user_type',)
    search_fields = ('name',)


@admin.register(UserPackage)
class UserPackageAdmin(admin.ModelAdmin):
    list_display = ('user', 'package', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__email',)

@admin.register(PackageFeature)
class PackageFeatureAdmin(admin.ModelAdmin):
    list_display = ('package', 'name')
    list_filter = ('package',)
    search_fields = ('name',)