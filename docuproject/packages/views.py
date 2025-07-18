from django.shortcuts import render, redirect, get_object_or_404
from .models import Package, UserPackage
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def guest_packages_view(request):
    packages = Package.objects.all()
    return render(request, 'packages/guest_packages.html', {'packages': packages})

@login_required
def user_packages_view(request):
    user = request.user
    packages = Package.objects.all()
    current_pkg = UserPackage.objects.filter(user=user).first()

    return render(request, 'packages/user_packages.html', {
        'packages': packages,
        'current_package': current_pkg
    })


@login_required
def activate_package(request, package_id):
    user = request.user

    # Block employee users
    if user.user_type == 'employee':
        messages.error(request, "Employees cannot activate packages. Please contact your company admin.")
        return redirect('packages:select_package')

    try:
        package = Package.objects.get(id=package_id)

        # Optional: Check if user is trying to activate an ineligible package
        if user.user_type == 'individual' and not package.for_individuals:
            messages.error(request, "This package is not available for individual users.")
            return redirect('packages:select_package')

        if user.user_type == 'company' and not package.for_companies:
            messages.error(request, "This package is not available for company users.")
            return redirect('packages:select_package')

        # Activate the package (pseudo-logic)
        user.active_package = package
        user.save()
        messages.success(request, f"{package.name} activated successfully!")

    except Package.DoesNotExist:
        messages.error(request, "Package not found.")

    return redirect('homepage')  # or wherever you want