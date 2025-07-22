# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.dashboard,name='dashboard'),
    path('dashboard/individual/', views.individual_dashboard, name='individual_dashboard'),
    path('dashboard/company/', views.company_dashboard, name='company_dashboard'),
    path('dashboard/employee/', views.employee_dashboard, name='employee_dashboard'),
    path('dashboard/superadmin/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('logout/', views.user_logout, name = 'logout'),
    path('dashboard/company/departments/', views.manage_departments, name='manage_departments'),
    path('dashboard/company/departments/edit/<int:dept_id>/', views.edit_department, name='edit_department'),
    path('dashboard/company/departments/delete/<int:dept_id>/', views.delete_department, name='delete_department'),
]
