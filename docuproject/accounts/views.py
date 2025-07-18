from django.shortcuts import render, redirect
from .forms import IndividualRegistrationForm, CompanyAdminRegistrationForm, EmployeeRegistrationForm, LoginForm
from django.contrib import messages
from django.contrib.auth import authenticate , login , logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from documents.models import Document
from django.db.models import Sum
from documents.forms import DocumentForm
from django.utils import timezone
from datetime import datetime
from .models import CustomUser, EmployeeProfile


def role_required(required_role):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.user_type == required_role:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Not allowed. Try entering with a different role.")
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
            return redirect('login')  # Change this to wherever you want to redirect

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
def dashboard(request):
    user = request.user
    if user.user_type == 'individual':
        return redirect('individual_dashboard')
    elif user.user_type == 'company':
        return redirect('company_dashboard')
    elif user.user_type == 'employee':
        return redirect('employee_dashboard')
    elif user.is_superuser or user.user_type == 'superadmin':
        return redirect('superadmin_dashboard')
    else:
        return render(request, 'errors/unauthorized.html')

@role_required('individual')    
@login_required
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
def company_dashboard(request):
    user = request.user  # Logged-in company admin
    # All documents uploaded by company + its employees
    employee_users = CustomUser.objects.filter(user_type='employee', employeeprofile__company=user)
    all_user_ids = [user.id] + list(employee_users.values_list('id', flat=True))
    company_documents = Document.objects.filter(owner_id__in=all_user_ids)


    total_documents = company_documents.count()

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
        'monthly_uploads': monthly_uploads,
        'employees' : employees
    }

    return render(request, 'accounts/company.html', context)

@role_required('employee')
@login_required
def employee_dashboard(request):
    # Fetch docs uploaded by this employee
    return render(request, 'accounts/employee.html')

@login_required
def superadmin_dashboard(request):
    # System-wide overview
    return render(request, 'accounts/superadmin.html')