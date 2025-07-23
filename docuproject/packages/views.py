from django.shortcuts import render, redirect, get_object_or_404
from packages.models import Package, UserPackage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta
from django.utils import timezone
from django.http import HttpResponseNotAllowed

def pricing_view(request):
    individual_packages = Package.objects.filter(user_type='individual')
    company_packages = Package.objects.filter(user_type='company')
    return render(request, 'packages/pricing.html', {
        'individual_packages': individual_packages,
        'company_packages': company_packages,
    })

@login_required
def payment_processing(request, package_id):
    # Show loading screen then auto-redirect to confirm
    if request.method == 'POST':
        package = get_object_or_404(Package, id=package_id)
        return render(request, 'packages/payment_processing.html', {'package': package})
    return redirect('packages:package_checkout', package_id=package_id)

@login_required
def package_checkout(request, package_id):
    user = request.user
    if hasattr(user, 'userpackage') and user.userpackage.is_active:
        messages.info(request, "You already have an active package.")
        return redirect('accounts:dashboard') 

    package = get_object_or_404(Package, id=package_id)
    return render(request, 'packages/checkout.html', {'package': package})

@login_required
def activate_package(request, package_id):
    user = request.user

    # Employees are not allowed to activate packages
    if user.user_type == 'employee':
        messages.error(request, "Employees cannot activate packages. Please contact your company admin.")
        return redirect('homepage')

    package = get_object_or_404(Package, id=package_id)

    # Ensure the package is eligible for the user's type
    if user.user_type == 'individual' and package.user_type != 'individual':
        messages.error(request, "This package is not available for individual users.")
        return redirect('packages:pricing')

    if user.user_type == 'company' and package.user_type != 'company':
        messages.error(request, "This package is not available for company users.")
        return redirect('packages:pricing')

    return redirect('packages:package_checkout', package_id=package_id)


@login_required
def confirm_payment(request, package_id):
    if request.method == 'POST':
        user = request.user
        package = get_object_or_404(Package, id=package_id)

        # Double check again
        if hasattr(user, 'userpackage') and user.userpackage.is_active:
            messages.warning(request, "You already have an active package.")
            return redirect('accounts:dashboard')

        # Simulate successful payment
        end_date = timezone.now().date() + timedelta(days=30)

        UserPackage.objects.create(
            user=user,
            package=package,
            end_date=end_date,
            is_active=True
        )

        messages.success(request, f"Package '{package.name}' activated successfully.")
        return redirect('accounts:dashboard')
    elif request.method != 'POST':
        return redirect('packages:package_checkout', package_id=package_id)
