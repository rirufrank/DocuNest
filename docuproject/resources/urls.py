from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('privacy/', views.privacy_policy, name='privacy'),
    path('data-protection/', views.data_protection_policy, name='data_protection'),
    path('terms/', views.terms_and_conditions, name='terms'),
]
