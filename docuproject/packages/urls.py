from django.urls import path
from . import views

app_name = 'packages'

urlpatterns = [
    path('view/', views.guest_packages_view, name='guest_packages'),
    path('select/', views.user_packages_view, name='user_packages'),
    path('activate/<int:package_id>/', views.activate_package, name='activate_package'),
]
