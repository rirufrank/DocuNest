from django.shortcuts import redirect
from functools import wraps

def package_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        # Only check if the user is authenticated
        if not user.is_authenticated:
            return redirect('accounts:login')

        # Skip check for employees (they inherit package)
        if user.user_type == 'employee':
            if not user.company or not hasattr(user.company, 'userpackage'):
                return redirect('accounts:dashboard')  # No company or no package
            return view_func(request, *args, **kwargs)

        # Check for userpackage (individual or company admin)
        if not hasattr(user, 'userpackage'):
            return redirect('packages:pricing')  # Redirect to package selection

        return view_func(request, *args, **kwargs)
    return _wrapped_view
