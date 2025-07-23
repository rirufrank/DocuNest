# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'
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
    path('dashboard/company/departments/create/', views.create_department, name='create_department'),
    path('dashboard/company/departments/edit/<int:dept_id>/', views.edit_department, name='edit_department'),
    path('dashboard/company/departments/delete/<int:dept_id>/', views.delete_department, name='delete_department'),
    path('department/remove/<int:employee_id>/', views.remove_from_department, name='remove_from_department'),
    path('department/assign/<int:employee_id>/<int:dept_id>/', views.assign_to_department, name='assign_to_department'),
    path('dashboard/company/employees/', views.manage_employees, name='manage_employees'),
    path('dashboard/company/employees/<int:employee_id>/toggle/', views.toggle_employee_status, name='toggle_employee_status'),
    path('dashboard/company/employees/<int:employee_id>/delete/', views.delete_employee, name='delete_employee'),
    path('dashboard/company/employees/<int:employee_id>/view/', views.view_employee_detail, name='view_employee_detail'),

    
]
