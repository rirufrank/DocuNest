# documents/urls.py

from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.documentredirect, name='documentredirect'),
    path('upload/', views.upload_document, name='upload_document'),
    path('download/<int:doc_id>/', views.download_document, name='download_document'),
    path('delete/<int:pk>/', views.delete_document, name='delete_document'),
    path('employee/', views.employeedocs, name= 'employeedocs'),
    path('individual/', views.individualdocs, name='individualdocs' ),
    path('company/', views.companydocs, name='companydocs'),
    path('documents/view/<int:doc_id>/', views.view_document, name='view_document'),
    path('toggle-favorite/<int:doc_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('details/<int:doc_id>/', views.document_detail, name='document_detail'),
]
