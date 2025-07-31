from django.shortcuts import render, redirect
from .forms import IndividualRegistrationForm,CompanyLogoForm, DepartmentForm, CompanyAdminRegistrationForm, EmployeeRegistrationForm, LoginForm, CompanyProfileForm
from django.contrib import messages
from django.contrib.auth import authenticate , login , logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from documents.models import Document
from django.db.models import Sum
from documents.forms import DocumentForm
from django.utils import timezone
from datetime import datetime,date
from django.shortcuts import get_object_or_404
from .models import CustomUser, EmployeeProfile, CompanyProfile, Department, get_user_storage_limit_mb
from packages.decorators import package_required
from functools import wraps
from packages.models import UserPackage
import math
from django.db.models import Q



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
        form_class = CompanyAdminRegistrationForm
    elif reg_type == 'employee':
        form_class = EmployeeRegistrationForm
    else:
        reg_type = 'individual'
        form_class = IndividualRegistrationForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES if reg_type == 'company' else None)

        if form.is_valid():
            if reg_type == 'employee':
                company_user = form.cleaned_data.get('company')

                if not company_user:
                    messages.error(request, "Please select a valid company.")
                    return render(request, 'accounts/register.html', {'form': form, 'type': reg_type})

                try:
                    user_package = UserPackage.objects.get(user=company_user, is_active=True)
                except UserPackage.DoesNotExist:
                    messages.error(request, "The company has no active subscription. Please contact the company administrator.")
                    return render(request, 'accounts/register.html', {'form': form, 'type': reg_type})

                # Check if company has room for another employee
                max_employees = user_package.package.max_employees
                current_count = CustomUser.objects.filter(
                    user_type='employee',
                    employeeprofile__company=company_user
                ).count()

                if current_count >= max_employees:
                    messages.error(request, f"The company has reached its employee limit of {max_employees}.")
                    return render(request, 'accounts/register.html', {'form': form, 'type': reg_type})

            # All validations passed
            form.save()
            messages.success(request, "Account created successfully. Please log in.")
            return redirect('accounts:login')
        else:
            messages.error(request, "Registration failed. Please check the form for errors.")
    else:
        form = form_class()

    return render(request, 'accounts/register.html', {'form': form, 'type': reg_type})
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # username = email
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.email}!")

                # Redirect superuser to admin site
                if user.is_superuser:
                    return redirect('/admin/')

                # Redirect regular user to homepage
                return redirect('homepage')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.warning(request, "Please enter correct details!")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('welcome')  

@login_required
def profile_redirect(request):
    user = request.user
    if user.user_type == 'individual':
        return redirect('accounts:individual_profile')
    elif user.user_type == 'company':
        return redirect('accounts:company_profile')
    elif user.user_type == 'employee':
        return redirect('accounts:employee_profile')
    else:
        return redirect('accounts:dashboard')  # fallback
    
@login_required
@role_required('employee')
def employee_profile(request):
    profile = request.user.employeeprofile

    if request.method == 'POST':
        phone = request.POST.get('phone')
        employee_code = request.POST.get('employee_code')
        profile_picture = request.FILES.get('profile_picture')

        if phone:
            profile.phone = phone
        if employee_code:
            profile.employee_code = employee_code
        if profile_picture:
            profile.profile_picture = profile_picture

        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('accounts:employee_profile')

    # Employee stats
    documents = Document.objects.filter(owner=request.user, trashed=False)
    doc_count = documents.count()
    storage_used_mb = round((documents.aggregate(total=Sum('size'))['total'] or 0) / (1024 * 1024), 2)

    # Company-wide stats
    company_user = profile.company  # This is the company admin (CustomUser instance)
    
    # Get all employees under the company
    company_employees = CustomUser.objects.filter(
        user_type='employee',
        employeeprofile__company=company_user
    )
    company_users = list(company_employees) + [company_user]  # include admin
    
    company_docs = Document.objects.filter(owner__in=company_users, trashed=False)
    
    company_doc_count = company_docs.count()
    company_storage_mb = round((company_docs.aggregate(total=Sum('size'))['total'] or 0) / (1024 * 1024), 2)
    
    try:
        user_package = UserPackage.objects.select_related('package').get(user=company_user)
        company_limit_gb = user_package.package.storage_limit_gb
    except UserPackage.DoesNotExist:
        company_limit_gb = 0
    

    context = {
        'profile': profile,
        'doc_count': doc_count,
        'storage_used_mb': storage_used_mb,
        'company_doc_count': company_doc_count,
        'company_storage_mb': company_storage_mb,
        'company_limit_gb': company_limit_gb
    }

    return render(request, 'accounts/profiles/profile_employee.html', context)


@login_required
@role_required('individual')
def individual_profile(request):
    profile = request.user.individualprofile

    # Get active package (if any)
    try:
        package_instance = UserPackage.objects.get(user=request.user, is_active=True)
        package = package_instance.package
        end_date = package_instance.end_date
    except UserPackage.DoesNotExist:
        package = None
        days_remaining = None

    # Handle profile updates
    if request.method == 'POST':
        phone = request.POST.get('phone')
        profile_picture = request.FILES.get('profile_picture')

        if phone:
            profile.phone = phone
        if profile_picture:
            profile.profile_picture = profile_picture

        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('accounts:individual_profile')

    context = {
        'profile': profile,
        'package': package,
        'package_instance': package_instance,
        'end_date': end_date,
    }
    return render(request, 'accounts/profiles/profile_individual.html', context)

@role_required('company')
@login_required
def company_profile(request):
    user = request.user
    company_profile = get_object_or_404(CompanyProfile, user=user)

    try:
        user_package = UserPackage.objects.get(user=user, is_active=True)
        package = user_package.package
        end_date = user_package.end_date
        days_remaining = (end_date - date.today()).days
    except UserPackage.DoesNotExist:
        package = None
        end_date = None
        days_remaining = None

    # Use one form (CompanyProfileForm) for now
    info_form = CompanyProfileForm(request.POST or None, request.FILES or None, instance=company_profile)

    if request.method == "POST":
        if info_form.is_valid():
            info_form.save()
            messages.success(request, "Profile information updated!")
            return redirect("accounts:company_profile")
        else:
            messages.error(request, "There were errors in the form. Please correct them.")

    employee_count = EmployeeProfile.objects.filter(company=user).count()
    department_count = Department.objects.filter(company=user).count()

    context = {
        'company': company_profile,
        'user': user,
        'package': package,
        'end_date': end_date,
        'days_remaining': days_remaining,
        'employee_count': employee_count,
        'department_count': department_count,
        'info_form': info_form,
    }
    return render(request, 'accounts/profiles/profile_company.html', context)

@login_required
def update_company_logo(request):
    if request.user.user_type != 'company':
        messages.error(request, "Unauthorized access.")
        return redirect('profile_redirect')  # or dashboard

    company = get_object_or_404(CompanyProfile, user=request.user)

    if request.method == 'POST':
        form = CompanyLogoForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Logo updated successfully!")
            return redirect('accounts:company_profile')  # or any other redirect
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CompanyLogoForm(instance=company)

    return render(request, 'accounts/profiles/company_logo_update.html', {
        'form': form,
        'company': company,
    })


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
        return redirect('/admin/')
    else:
        return render(request, 'errors/unauthorized.html')

@role_required('individual')    
@login_required
@package_required
def individual_dashboard(request):
    user = request.user
    profile = user.individualprofile

    profile_picture_url = (
        profile.profile_picture.url if profile.profile_picture else '/static/images/default-avatar.png'
    )

    documents = Document.objects.filter(owner=request.user).order_by('-uploaded_at')[:4]
    total_documents = Document.objects.filter(owner=request.user).count()

    documents_qs = Document.objects.filter(owner=request.user)
    total_storage_bytes = sum([doc.file.size for doc in documents_qs if doc.file])
    total_storage_mb = round(total_storage_bytes / (1024 * 1024), 2)

    INDIVIDUAL_STORAGE_LIMIT_MB = get_user_storage_limit_mb(request.user)
    storage_percent = min(100, round((total_storage_mb / INDIVIDUAL_STORAGE_LIMIT_MB) * 100, 2))

    favorite_count = Document.objects.filter(owner=request.user, is_favorite=True).count()

    form = DocumentForm(request.POST, request.FILES)
    if form.is_valid():
        document = form.save(commit=False)
        document.owner = request.user
        if request.user.user_type == 'individual':
            document.department = None
        document.save()
        form.save_m2m()
        messages.success(request, "Document uploaded successfully.")
        return redirect('accounts:individual_dashboard')

    context = {
        'form': form,
        'documents': documents,
        'total_documents': total_documents,
        'total_storage_mb': total_storage_mb,
        'storage_percent': storage_percent,
        'storage_limit_mb': INDIVIDUAL_STORAGE_LIMIT_MB,
        'favorite_count': favorite_count,
        'profile_picture_url': profile_picture_url,
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
def employee_dashboard(request):
    employee_profile = request.user.employeeprofile  # This assumes a OneToOne link
    return render(request, 'accounts/employee.html', {
        'employee': employee_profile
    })


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
        return redirect('accounts:manage_departments')  

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
