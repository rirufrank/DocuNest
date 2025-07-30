from django.urls import path
from . import views

urlpatterns = [
    path('preview/<str:template_name>/', views.preview_template, name='preview-template'),
    path('',views.welcome, name= 'welcome'),
    path('homepage/', views.homepage, name='homepage'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('services/', views.services, name='services'),
    path('help/', views.help_home, name='help'),
]
