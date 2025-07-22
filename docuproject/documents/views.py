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
from datetime import timedelta
from django.utils.timezone import now



def role_required(required_role):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.user_type == required_role:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Not allowed. Try entering with a different role.")
        return _wrapped_view
    return decorator


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
def document_list(request):
    docs = Document.objects.filter(owner=request.user, trashed=False)
    return render(request, 'documents/list.html', {'documents': docs})



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
    documents_qs = Document.objects.filter(owner=user, trashed=False)

    # Search by title
    q = request.GET.get("q")
    if q:
        documents_qs = documents_qs.filter(title__icontains=q)

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
            start = today - timedelta(days=90)
            documents_qs = documents_qs.filter(uploaded_at__date__gte=start)
        elif date_filter == "last_year":
            last_year = today.year - 1
            documents_qs = documents_qs.filter(uploaded_at__year=last_year)

    # File type group filter (uses model method)
    selected_group = request.GET.get("file_type")
    if selected_group:
        documents_qs = [doc for doc in documents_qs if doc.categorize_file_type() == selected_group]
    else:
        documents_qs = list(documents_qs)  # ensure it's a list for pagination below

    # Sorting
    sort_by = request.GET.get("sort")
    if sort_by == "oldest":
        documents_qs = sorted(documents_qs, key=lambda d: d.uploaded_at)
    elif sort_by == "size":
        documents_qs = sorted(documents_qs, key=lambda d: d.size or 0, reverse=True)
    else:
        documents_qs = sorted(documents_qs, key=lambda d: d.uploaded_at, reverse=True)

    # File type groups available (from unfiltered queryset)
    all_documents = Document.objects.filter(owner=user, trashed=False)
    file_type_groups = sorted(set(doc.categorize_file_type() for doc in all_documents if doc.file_type))

    # Pagination
    paginator = Paginator(documents_qs, 16)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "documents": page_obj,
        "query": q,
        "file_type_groups": file_type_groups,
        "selected_group": selected_group,
        "department": department,
        "sort_by": sort_by,
        "date_filter": date_filter,
        "all_file_types": all_documents.values_list("file_type", flat=True).distinct(),
    }
    return render(request, 'documents/individualdocs.html', context)


@role_required('individual')
@login_required
def individualdocs(request):
    user = request.user
    documents_qs = Document.objects.filter(owner=user, trashed=False)

    # Search by title
    q = request.GET.get("q") or ""
    if q:
        documents_qs = documents_qs.filter(title__icontains=q)

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
            start = today - timedelta(days=90)
            documents_qs = documents_qs.filter(uploaded_at__date__gte=start)
        elif date_filter == "last_year":
            last_year = today.year - 1
            documents_qs = documents_qs.filter(uploaded_at__year=last_year)

    # File extension filter
    ext = request.GET.get("extension", "").lower()
    if ext:
        documents_qs = documents_qs.filter(file__iendswith=f".{ext}")

    # Turn into list to allow custom sorting and file type grouping
    documents_qs = list(documents_qs)

    # File type group filter
    selected_group = request.GET.get("file_type")
    if selected_group:
        documents_qs = [doc for doc in documents_qs if doc.categorize_file_type() == selected_group]

    # Sorting
    sort_by = request.GET.get("sort")
    if sort_by == "oldest":
        documents_qs = sorted(documents_qs, key=lambda d: d.uploaded_at)
    elif sort_by == "size":
        documents_qs = sorted(documents_qs, key=lambda d: d.size or 0, reverse=True)
    else:
        documents_qs = sorted(documents_qs, key=lambda d: d.uploaded_at, reverse=True)

    # File type groups for filters
    all_documents = Document.objects.filter(owner=user, trashed=False)
    file_type_groups = sorted(set(doc.categorize_file_type() for doc in all_documents if doc.file_type))
    all_extensions = sorted(set(doc.file_extension() for doc in all_documents if doc.file_extension()))

    # Pagination
    paginator = Paginator(documents_qs, 16)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "documents": page_obj,
        "query": q,
        "file_type_groups": file_type_groups,
        "selected_group": selected_group,
        "sort_by": sort_by,
        "date_filter": date_filter,
        "all_file_types": all_documents.values_list("file_type", flat=True).distinct(),
        "selected_extension": ext,
        "all_extensions": all_extensions,
    }
    return render(request, 'documents/individualdocs.html', context)
