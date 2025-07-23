# documents/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import DocumentForm
from .models import Document
from django.http import HttpResponseForbidden
from django.http import FileResponse, Http404
from django.core.paginator import Paginator
from django.contrib import messages
from collections import Counter
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Q
from accounts.models import CustomUser, EmployeeProfile
from django.db.models import Prefetch
from functools import wraps
import mimetypes



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
    elif user.user_type == 'accounts:company':
        return redirect('companydocs')
    elif user.user_type == 'documents:employee':
        return redirect('accounts:employeedocs')
    else:
        return redirect('accounts:login')  # or show error

@login_required
def view_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)
    user = request.user

    # Check access
    if (
        document.owner == user or
        user in document.shared_with.all() or
        (user.user_type == 'employee' and document.owner.company == user.company)
    ):
        file_path = document.file.path

        try:
            # Guess content type (e.g., application/pdf, image/jpeg)
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'  # fallback

            return FileResponse(
                open(file_path, 'rb'),
                content_type=content_type
            )
        except FileNotFoundError:
            raise Http404("File not found.")
    else:
        raise Http404("You do not have permission to view this document.")
 
@login_required
def download_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)

    # Check access control
    user = request.user
    if (
        document.owner == user or
        user in document.shared_with.all() or
        (user.user_type == 'employee' and document.owner.company == user.company)
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
            doc = form.save(commit=False)
            doc.owner = request.user

            # Set department only if employee
            if hasattr(request.user, 'employeeprofile'):
                doc.department = request.user.employeeprofile.department_name
            else:
                doc.department = ''  # Individuals leave this blank

            doc.save()
            form.save_m2m()
            return redirect('document_list')  # or your dashboard
    else:
        form = DocumentForm()
    return render(request, 'documents/upload.html', {'form': form})


@login_required
def download_document(request, doc_id):
    try:
        doc = Document.objects.get(id=doc_id, owner=request.user)
        return FileResponse(doc.file.open('rb'), as_attachment=True, filename=doc.file.name)
    except Document.DoesNotExist:
        raise Http404("Document not found.")

@login_required
def delete_document(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)

    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Document deleted successfully.')
        return redirect('documents:my_documents')

    return render(request, 'documents/confirm_delete.html', {'document': document})


@role_required('employee')
@login_required
def employeedocs(request):
    user = request.user
    documents = Document.objects.filter(
        owner=user,
        trashed=False
    ).select_related(
        'owner',
        'owner__employeeprofile',
        'owner__employeeprofile__department'
    )

    # Fetch filters from GET
    query = request.GET.get("q", "")
    file_type = request.GET.get("file_type", "")
    department = request.GET.get("department", "")
    date_filter = request.GET.get("date_filter", "")
    sort_by = request.GET.get("sort", "")

    # Search by title or file name
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(file__icontains=query)
        )

    # Filter by file type (e.g. "Images", "PDFs")
    if file_type:
        if file_type == "Images":
            documents = documents.filter(file__iendswith__in=[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico"])
        elif file_type == "PDFs":
            documents = documents.filter(file__iendswith=".pdf")
        elif file_type == "Word Docs":
            documents = documents.filter(file__iendswith__in=[".doc", ".docx"])
        elif file_type == "Spreadsheets":
            documents = documents.filter(file__iendswith__in=[".xls", ".xlsx", ".csv"])
        # etc...

    # Filter by department name (related field)
    if department:
        documents = documents.filter(owner__employeeprofile__department__name__icontains=department)

    # Date filter
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

    # Sort
    if sort_by == "oldest":
        documents = documents.order_by("uploaded_at")
    elif sort_by == "size":
        documents = documents.order_by("-file_size")
    else:  # Newest first
        documents = documents.order_by("-uploaded_at")

    context = {
        "documents": documents,
        "query": query,
        "file_type_groups": ["Images", "PDFs", "Word Docs", "Spreadsheets"],
        "selected_group": file_type,
        "department": department,
        "date_filter": date_filter,
        "sort_by": sort_by,
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
        documents_qs = documents_qs.filter(title__icontains=query)

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

    # Pagination
    paginator = Paginator(documents_list, 16)
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
    }
    return render(request, 'documents/individualdocs.html', context)

@role_required('company')
@login_required
def companydocs(request):
    employees = CustomUser.objects.filter(
        user_type='employee',
        employeeprofile__company=request.user
    ).prefetch_related('employeeprofile')

    documents = Document.objects.filter(
        owner__in=employees,
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
    department = request.GET.get('department')
    if department:
        documents = documents.filter(owner__employeeprofile__department__name=department)

    # Sort
    sort = request.GET.get('sort', 'recent')
    if sort == 'recent':
        documents = documents.order_by('-uploaded_at')
    elif sort == 'oldest':
        documents = documents.order_by('uploaded_at')

    departments = EmployeeProfile.objects.filter(
        company=request.user
    ).values_list('department__name', flat=True).distinct()

    context = {
        'documents': documents,
        'employees': employees,
        'departments': departments,
        'q': q,
        'emp_id': emp_id,
        'department_filter': department,
        'sort': sort,
    }

    return render(request, 'documents/companydocs.html', context)
