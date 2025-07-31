# documents/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import DocumentForm
from .models import Document
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.http import FileResponse, Http404
from django.core.paginator import Paginator, EmptyPage , PageNotAnInteger
from django.contrib import messages
from collections import Counter
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Q
from accounts.models import CustomUser, EmployeeProfile, Department
from django.db.models import Prefetch
from functools import wraps
import mimetypes
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied


def role_required(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.user_type == required_role:
                return view_func(request, *args, **kwargs)
            # Render a redirect warning page
            return render(request, "403_redirect.html", {
                "message": "Access denied. You will be redirected to the homepage in 5 seconds.",
                "redirect_url": "/homepage",
                "delay": 5000  # in milliseconds
            })
        return _wrapped_view
    return decorator

def documentredirect(request):
    user = request.user

    if user.user_type == 'individual':
        return redirect('documents:individualdocs')
    elif user.user_type == 'company':
        return redirect('documents:companydocs')
    elif user.user_type == 'employee':
        return redirect('documents:employeedocs')
    else:
        return redirect('/admin/')

@login_required
def view_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)
    user = request.user

    user_company = None
    if user.user_type == 'employee' and hasattr(user, 'employeeprofile'):
        user_company = user.employeeprofile.company

    if (
        document.owner == user or
        user in document.shared_with.all() or
        (user.user_type == 'employee' and (
            document.owner == user_company or
            (document.is_company_wide and document.owner == user_company)
        )) or
        (user.user_type == 'company' and hasattr(user, 'companyprofile') and
         hasattr(document.owner, 'employeeprofile') and
         document.owner.employeeprofile.company == user)
    ):
        file_path = document.file.path
        try:
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'
            return FileResponse(open(file_path, 'rb'), content_type=content_type)
        except FileNotFoundError:
            raise Http404("File not found.")
    else:
        raise Http404("You do not have permission to view this document.")

    
@login_required
def document_detail(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)
    user = request.user

    user_company = None
    if user.user_type == 'employee' and hasattr(user, 'employeeprofile'):
        user_company = user.employeeprofile.company

    if (
        document.owner == user or
        user in document.shared_with.all() or
        (user.user_type == 'employee' and (
            document.owner == user_company or
            (document.is_company_wide and document.owner == user_company)
        )) or
        (user.user_type == 'company' and hasattr(user, 'companyprofile') and
         hasattr(document.owner, 'employeeprofile') and
         document.owner.employeeprofile.company == user)
    ):
        return render(request, 'documents/document_detail.html', {'document': document})
    else:
        return render(request, '403_redirect.html')



@login_required
def download_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)
    user = request.user

    user_company = None
    if user.user_type == 'employee' and hasattr(user, 'employeeprofile'):
        user_company = user.employeeprofile.company

    if (
        document.owner == user or
        user in document.shared_with.all() or
        (user.user_type == 'employee' and (
            document.owner == user_company or
            (document.is_company_wide and document.owner == user_company)
        )) or
        (user.user_type == 'company' and hasattr(user, 'companyprofile') and
         hasattr(document.owner, 'employeeprofile') and
         document.owner.employeeprofile.company == user)
    ):
        try:
            return FileResponse(document.file.open('rb'), content_type='application/octet-stream')
        except FileNotFoundError:
            raise Http404("File not found.")
    else:
        raise Http404("You do not have permission to view this document.")



@login_required
def upload_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)

        if form.is_valid():
            # Check for inactive employee AFTER form is valid
            user = request.user
            if user.user_type == 'employee' and hasattr(user, 'employeeprofile'):
                if not user.employeeprofile.is_active:
                    messages.error(request, "Upload failed. Your account is inactive. Please contact your company admin.")
                    return render(request, 'documents/upload.html', {'form': form})

            doc = form.save(commit=False)
            doc.owner = user

            if hasattr(user, 'employeeprofile'):
                doc.department = user.employeeprofile.department or ''
                doc.is_company_wide = False
            elif user.user_type == 'company':
                doc.is_company_wide = True
                doc.department = ''
            else:
                doc.is_company_wide = False
                doc.department = ''

            try:
                doc.full_clean()
                doc.save()
                form.save_m2m()
                messages.success(request, "Document uploaded successfully.")
                return redirect('documents:upload_document')
            except ValidationError as e:
                messages.error(request, f"Validation failed: {e}")
        else:
            messages.error(request, "Upload failed. Please check the file type and size.")
    else:
        form = DocumentForm()

    return render(request, 'documents/upload.html', {'form': form})

@login_required
def delete_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    user = request.user

    can_delete = (
        document.owner == user or
        (
            user.user_type == 'company' and
            document.owner.user_type == 'employee' and
            document.owner.employeeprofile.company == user
        )
    )

    if not can_delete:
        return HttpResponseForbidden("You do not have permission to delete this document.")

    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Document deleted successfully.')
        return redirect('documents:documentredirect')

    return render(request, 'documents/confirm_delete.html', {'document': document})


@role_required('employee')
@login_required
def employeedocs(request):
    user = request.user
    company = user.employeeprofile.company  # Get the employee's company

    documents = Document.objects.filter(
        Q(owner=user) |
        Q(owner=company, is_company_wide=True),
        trashed=False
    ).select_related(
        'owner',
        'owner__employeeprofile',
        'owner__employeeprofile__department'
    )

    # Filters from GET
    query = request.GET.get("q", "")
    file_type = request.GET.get("file_type", "")
    department = request.GET.get("department", "")
    date_filter = request.GET.get("date_filter", "")
    sort_by = request.GET.get("sort", "")
    favorites = request.GET.get("favorites")

    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(file__icontains=query)
        )

    if file_type:
        if file_type == "Images":
            documents = documents.filter(file__iendswith__in=[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico"])
        elif file_type == "PDFs":
            documents = documents.filter(file__iendswith=".pdf")
        elif file_type == "Word Docs":
            documents = documents.filter(file__iendswith__in=[".doc", ".docx"])
        elif file_type == "Spreadsheets":
            documents = documents.filter(file__iendswith__in=[".xls", ".xlsx", ".csv"])

    if department:
        documents = documents.filter(owner__employeeprofile__department__name__icontains=department)

    if date_filter:
        now = timezone.now()
        if date_filter == "today":
            documents = documents.filter(uploaded_at__date=now.date())
        elif date_filter == "this_week":
            start = now - timedelta(days=now.weekday())
            documents = documents.filter(uploaded_at__date__gte=start.date())
        elif date_filter == "this_month":
            documents = documents.filter(uploaded_at__month=now.month, uploaded_at__year=now.year)
        elif date_filter == "last_3_months":
            three_months_ago = now - timedelta(days=90)
            documents = documents.filter(uploaded_at__date__gte=three_months_ago)
        elif date_filter == "last_year":
            last_year = now.year - 1
            documents = documents.filter(uploaded_at__year=last_year)

    if favorites == "1":
        documents = documents.filter(is_favorite=True)

    if sort_by == "oldest":
        documents = documents.order_by("uploaded_at")
    elif sort_by == "size":
        documents = documents.order_by("-file_size")
    else:
        documents = documents.order_by("-uploaded_at")

    # Pagination
    paginator = Paginator(documents, 12)
    page = request.GET.get("page")
    try:
        documents = paginator.page(page)
    except PageNotAnInteger:
        documents = paginator.page(1)
    except EmptyPage:
        documents = paginator.page(paginator.num_pages)

    context = {
        "documents": documents,
        "query": query,
        "file_type_groups": ["Images", "PDFs", "Word Docs", "Spreadsheets"],
        "selected_group": file_type,
        "department": department,
        "date_filter": date_filter,
        "sort_by": sort_by,
        "favorites": favorites,
    }

    return render(request, "documents/employeedocs.html", context)


@role_required('individual')
@login_required
def individualdocs(request):
    user = request.user
    documents_qs = Document.objects.filter(owner=user, trashed=False)

    # Search by title
    query = request.GET.get("q", "").strip()
    if query:
        documents_qs = documents_qs.filter(
            Q(title__icontains=query) |
            Q(file__icontains=query)
            )

    # Department filter
    department = request.GET.get("department")
    if department:
        documents_qs = documents_qs.filter(department__icontains=department)

    # Date range filter
    date_filter = request.GET.get("date_filter")
    if date_filter:
        today = now().date()
        if date_filter == "today":
            documents_qs = documents_qs.filter(uploaded_at__date=today)
        elif date_filter == "this_week":
            start = today - timedelta(days=today.weekday())
            documents_qs = documents_qs.filter(uploaded_at__date__gte=start)
        elif date_filter == "this_month":
            documents_qs = documents_qs.filter(uploaded_at__month=today.month, uploaded_at__year=today.year)
        elif date_filter == "last_3_months":
            documents_qs = documents_qs.filter(uploaded_at__date__gte=today - timedelta(days=90))
        elif date_filter == "last_year":
            documents_qs = documents_qs.filter(uploaded_at__year=today.year - 1)

    # File extension filter
    selected_extension = request.GET.get("extension", "").lower()
    if selected_extension:
        documents_qs = documents_qs.filter(file__iendswith=f".{selected_extension}")

    # Convert to list for further processing
    documents_list = list(documents_qs)

    # File type group filter (Image, Document, etc.)
    selected_group = request.GET.get("file_type")
    if selected_group:
        documents_list = [doc for doc in documents_list if doc.categorize_file_type() == selected_group]

    # Sorting
    sort_by = request.GET.get("sort")
    if sort_by == "oldest":
        documents_list = sorted(documents_list, key=lambda d: d.uploaded_at)
    elif sort_by == "size":
        documents_list = sorted(documents_list, key=lambda d: d.size or 0, reverse=True)
    else:
        documents_list = sorted(documents_list, key=lambda d: d.uploaded_at, reverse=True)

    # All documents for filters
    all_documents = Document.objects.filter(owner=user, trashed=False)
    file_type_groups = sorted(set(doc.categorize_file_type() for doc in all_documents))
    all_extensions = sorted(set(doc.file_extension() for doc in all_documents if doc.file_extension()))

    # Favorites filter
    favorites_only = request.GET.get("favorites") == "on"
    if favorites_only:
        documents_list = [doc for doc in documents_list if doc.is_favorite]

    # Pagination
    paginator = Paginator(documents_list, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "documents": page_obj,
        "query": query,
        "file_type_groups": file_type_groups,
        "selected_group": selected_group,
        "sort_by": sort_by,
        "date_filter": date_filter,
        "selected_extension": selected_extension,
        "all_extensions": all_extensions,
        "favorites_only": favorites_only,
    }
    return render(request, 'documents/individualdocs.html', context)

@role_required('company')
@login_required
def companydocs(request):
    employees = CustomUser.objects.filter(
        user_type='employee',
        employeeprofile__company=request.user
    ).prefetch_related('employeeprofile')

    # Include both employee documents and company admin documents
    documents = Document.objects.filter(
        Q(owner__in=employees) | Q(owner=request.user),
        trashed=False
    ).select_related(
        'owner',
        'owner__employeeprofile',
        'owner__employeeprofile__department'
    )

    # Search
    q = request.GET.get('q', '')
    if q:
        documents = documents.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )

    # Filter by employee
    emp_id = request.GET.get('employee')
    if emp_id:
        documents = documents.filter(owner__id=emp_id)

    # Filter by department
    department_filter = request.GET.get('department', 'all')
    if department_filter == 'none':
        documents = documents.filter(owner__employeeprofile__department__isnull=True)
    elif department_filter != 'all':
        documents = documents.filter(owner__employeeprofile__department__name=department_filter)


    # Sort
    sort = request.GET.get('sort', 'recent')
    if sort == 'recent':
        documents = documents.order_by('-uploaded_at')
    elif sort == 'oldest':
        documents = documents.order_by('uploaded_at')

    # Pagination
    paginator = Paginator(documents, 16)  # Show X documents per page
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    departments = EmployeeProfile.objects.filter(
        company=request.user
    ).values_list('department__name', flat=True).distinct()

    context = {
        'page_obj': page_obj,               # This replaces 'documents'
        'employees': employees,
        "departments": Department.objects.values_list('name', flat=True),
        'q': q,
        'emp_id': emp_id,
        'department_filter': department_filter,
        'sort': sort,
    }

    return render(request, 'documents/companydocs.html', context)


@login_required
@require_POST
def toggle_favorite(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    # Only the owner can toggle
    if document.owner != request.user:
        return HttpResponseForbidden("You don't have permission to favorite this document.")

    # Toggle the favorite status
    document.is_favorite = not document.is_favorite
    document.save()

    # Redirect back to the document detail page
    return redirect('documents:document_detail', doc_id=doc_id)