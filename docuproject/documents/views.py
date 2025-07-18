# documents/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import DocumentForm
from .models import Document
from django.http import FileResponse, Http404
from django.contrib import messages

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