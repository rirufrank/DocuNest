from django.urls import path
from . import views

app_name = 'packages'

urlpatterns = [
    path('view/', views.pricing_view, name='pricing'),
    path('activate/<int:package_id>/', views.activate_package, name='activate_package'),
    path('checkout/<int:package_id>/', views.package_checkout, name='package_checkout'),
    path('confirm-payment/<int:package_id>/', views.confirm_payment, name='confirm_payment'),
    path('processing/<int:package_id>/', views.payment_processing, name='payment_processing'),
]
