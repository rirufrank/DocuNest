from django.shortcuts import render, redirect
from .forms import IndividualRegistrationForm,DepartmentForm, CompanyAdminRegistrationForm, EmployeeRegistrationForm, LoginForm
from django.contrib import messages
from django.contrib.auth import authenticate , login , logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from documents.models import Document
from django.db.models import Sum
from documents.forms import DocumentForm
from django.utils import timezone
from datetime import datetime
from django.shortcuts import get_object_or_404
from .models import CustomUser, EmployeeProfile, CompanyProfile, Department
from packages.decorators import package_required
from functools import wraps


def role_required(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.user_type == required_role:
                return view_func(request, *args, **kwargs)
            # Render a redirect warning page
            return render(request, "403_redirect.html", {
                "message": "Access denied. You will be redirected to the homepage in 5 seconds.",
                "redirect_url": "/",
                "delay": 5000  # in milliseconds
            })
        return _wrapped_view
    return decorator

def register(request):
    reg_type = request.GET.get('type', 'individual')

    if reg_type == 'company':
        form = CompanyAdminRegistrationForm()
    elif reg_type == 'employee':
        form = EmployeeRegistrationForm()
    else:
        reg_type = 'individual'
        form = IndividualRegistrationForm()

    if request.method == 'POST':
        if reg_type == 'company':
            form = CompanyAdminRegistrationForm(request.POST, request.FILES)
        elif reg_type == 'employee':
            form = EmployeeRegistrationForm(request.POST)
        else:
            form = IndividualRegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('accounts:login')  

    return render(request, 'accounts/register.html', {'form': form, 'type': reg_type})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # username is actually email
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome {user.email}!")
                return redirect('homepage')  # Set this to your post-login destination
            else:
                messages.error(request, "Invalid credentials")
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('welcome')  

@login_required
@package_required
def dashboard(request):
    user = request.user
    if user.user_type == 'individual':
        return redirect('accounts:individual_dashboard')
    elif user.user_type == 'company':
        return redirect('accounts:company_dashboard')
    elif user.user_type == 'employee':
        return redirect('accounts:employee_dashboard')
    elif user.is_superuser or user.user_type == 'superadmin':
        return redirect('superadmin_dashboard')
    else:
        return render(request, 'errors/unauthorized.html')

@role_required('individual')    
@login_required
@package_required
def individual_dashboard(request):
    documents = Document.objects.filter(owner=request.user).order_by('-uploaded_at')[:4]
    total_documents = Document.objects.filter(owner=request.user).count()

    documents_qs = Document.objects.filter(owner=request.user)
    total_storage_bytes = sum([doc.file.size for doc in documents_qs if doc.file])
    total_storage_mb = round(total_storage_bytes / (1024 * 1024), 2)

    INDIVIDUAL_STORAGE_LIMIT_MB = 100
    storage_percent = min(100, round((total_storage_mb / INDIVIDUAL_STORAGE_LIMIT_MB) * 100, 2))

    form = DocumentForm(request.POST, request.FILES)
    if form.is_valid():
        document = form.save(commit=False)
        document.owner = request.user
        if request.user.user_type == 'individual':
            document.department = None
        document.save()
        form.save_m2m()
        messages.success(request, "Document uploaded successfully.")
        return redirect('individual_dashboard')

    context = {
        'form': form,
        'documents': documents,
        'total_documents': total_documents,
        'total_storage_mb': total_storage_mb,
        'storage_percent': storage_percent,
        'storage_limit_mb': INDIVIDUAL_STORAGE_LIMIT_MB,
    }
    return render(request, 'accounts/individual.html', context)

@role_required('company')
@login_required
@package_required
def company_dashboard(request):
    user = request.user  # Logged-in company admin
    user_package = getattr(user, 'userpackage', None)
    # All documents uploaded by company + its employees
    employee_users = CustomUser.objects.filter(user_type='employee', employeeprofile__company=user)
    all_user_ids = [user.id] + list(employee_users.values_list('id', flat=True))
    company_documents = Document.objects.filter(owner_id__in=all_user_ids)


    total_documents = company_documents.count()
    #Company details
    company_profile = CompanyProfile.objects.get(user=request.user)

    # Calculate storage usage in MB or GB (assumes `document.file.size`)
    total_storage_used = sum(doc.file.size for doc in company_documents)  # bytes
    used_storage_gb = round(total_storage_used / (1024 ** 3), 2)
    total_storage_gb = 50  # example package limit
    storage_percent = round((used_storage_gb / total_storage_gb) * 100, 1)

    # Employees count
    employee_count = employee_users.count()
    company = request.user
    employees = EmployeeProfile.objects.filter(company=company).select_related('user')
    for emp in employees:
        emp.upload_count = Document.objects.filter(owner=emp.user).count()

    # Documents uploaded this month
    now = timezone.now()
    monthly_uploads = company_documents.filter(uploaded_at__year=now.year, uploaded_at__month=now.month).count()
    
    context = {
        'total_documents': total_documents,
        'used_storage_gb': used_storage_gb,
        'total_storage_gb': total_storage_gb,
        'storage_percent': min(storage_percent, 100),  # cap at 100
        'employee_count': employee_count,
        'company_profile': company_profile,
        'monthly_uploads': monthly_uploads,
        'employees' : employees,
        'user_package': user_package,
    }

    return render(request, 'accounts/company.html', context)

@role_required('employee')
@login_required
@package_required
def employee_dashboard(request):
    # Fetch docs uploaded by this employee
    return render(request, 'accounts/employee.html')

@login_required
def superadmin_dashboard(request):
    # System-wide overview
    return render(request, 'accounts/superadmin.html')

@role_required('company')
@login_required
@package_required
def manage_departments(request):
    company_user = request.user
    departments = Department.objects.filter(company=company_user)

    # Calculate remaining slots
    max_departments = company_user.userpackage.package.max_departments if hasattr(company_user, 'userpackage') else 0
    current_count = departments.count()
    can_add_department = current_count < max_departments

    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save(commit=False)
            department.company = company_user
            department.save()
            return redirect('accounts:manage_departments')
    else:
        form = DepartmentForm()

    return render(request, 'accounts/company/manage_departments.html', {
        'departments': departments,
        'form': form,
        'can_add_department': can_add_department,
        'max_departments': max_departments,
        'current_count': current_count,
    })

@login_required
@role_required('company')
@package_required
def edit_department(request, dept_id):
    employees = EmployeeProfile.objects.filter(company=request.user)
    company = request.user
    department = get_object_or_404(Department, id=dept_id, company=company)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        to_assign = request.POST.getlist('assign_employees')
        to_remove = request.POST.getlist('remove_employees')

        if form.is_valid():
            form.save()

            # Assign selected employees
            EmployeeProfile.objects.filter(id__in=to_assign, company=company).update(department=department)

            # Remove selected employees from department
            EmployeeProfile.objects.filter(id__in=to_remove, company=company, department=department).update(department=None)

            messages.success(request, "Department updated.")
            return redirect('accounts:manage_departments')

    else:
        form = DepartmentForm(instance=department)

    # Get employees
    assigned_employees = EmployeeProfile.objects.filter(company=company, department=department)
    unassigned_employees = EmployeeProfile.objects.filter(company=company, department__isnull=True)
    available_departments = Department.objects.filter(company=request.user)

    return render(request, 'accounts/company/edit_departments.html', {
        'form': form,
        'department': department,
        'assigned_employees': assigned_employees,
        'unassigned_employees': unassigned_employees,
        'available_departments': available_departments,
    })


@login_required
@role_required('company')
@package_required
def remove_from_department(request, employee_id):
    emp = get_object_or_404(EmployeeProfile, id=employee_id, company=request.user)

    # Store the department ID before removing
    dept_id = emp.department.id if emp.department else None

    if dept_id:
        emp.department = None
        emp.save()
        return redirect('accounts:edit_department', dept_id=dept_id)

    else:
        return redirect('accounts:manage_departments')  # fallback in case no department was found


@login_required
@role_required('company')
@package_required
def assign_to_department(request, employee_id, dept_id):
    emp = get_object_or_404(EmployeeProfile, id=employee_id, company=request.user)
    dept = get_object_or_404(Department, id=dept_id, company=request.user)
    emp.department = dept
    emp.save()
    return redirect('accounts:edit_department', dept_id=dept_id)

@login_required
@package_required
@role_required('company')
def delete_department(request, dept_id):
    department = get_object_or_404(Department, id=dept_id, company=request.user)
    department.delete()
    return redirect('accounts:manage_departments')

@login_required
@role_required('company')
@package_required
def create_department(request):
    user = request.user

    # Enforce department limit from package
    current_count = Department.objects.filter(company=user).count()
    max_departments = user.userpackage.package.max_departments if hasattr(user, 'userpackage') else 0

    if current_count >= max_departments:
        messages.error(request, f"You've reached the maximum of {max_departments} departments for your package.")
        return redirect('accounts:manage_departments')  # ✅ plural

    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save(commit=False)
            department.company = user
            department.save()
            messages.success(request, "Department created successfully.")
            return redirect('accounts:manage_departments')
    else:
        form = DepartmentForm()

    return render(request, 'accounts/company/create_department.html', {'form': form})

@package_required
@role_required('company')
@login_required
def manage_employees(request):
    employees = CustomUser.objects.filter(
        user_type='employee',
        employeeprofile__company=request.user
    )
    return render(request, 'accounts/company/manage_employees.html', {'employees': employees})

@package_required
@role_required('company')
@login_required
def toggle_employee_status(request, employee_id):
    employee = get_object_or_404(
        CustomUser,
        id=employee_id,
        user_type='employee',
        employeeprofile__company=request.user
    )
    profile = employee.employeeprofile
    profile.is_active = not profile.is_active
    profile.save()
    return redirect('accounts:manage_employees')


@package_required
@role_required('company')
@login_required
def delete_employee(request, employee_id):
    employee = get_object_or_404(
        CustomUser,
        id=employee_id,
        user_type='employee',
        employeeprofile__company=request.user
    )

    if request.method == 'POST':
        password = request.POST.get('password')
        admin = authenticate(request, email=request.user.email, password=password)

        if admin is not None:
            employee.delete()
            messages.success(request, "Employee deleted successfully.")
            return redirect('accounts:manage_employees')
        else:
            messages.error(request, "Incorrect password. Deletion aborted.")

    return render(request, 'accounts/company/confirm_delete_employee.html', {
        'employee': employee
    })

@package_required
@role_required('company')
@login_required
def view_employee_detail(request, employee_id):
    employee = get_object_or_404(
        CustomUser.objects.select_related('employeeprofile'),
        id=employee_id,
        user_type='employee',
        employeeprofile__company=request.user
    )

    #Count of documents uploaded by this employee
    document_count = employee.documents.count()

    context = {
        'employee': employee,
        'profile': employee.employeeprofile,
        'document_count': document_count,
    }
    return render(request, 'accounts/company/view_employee_detail.html', context)
