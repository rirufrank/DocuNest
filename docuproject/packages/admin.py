from django.contrib import admin
from .models import Package, UserPackage

admin.site.register(Package)
admin.site.register(UserPackage)