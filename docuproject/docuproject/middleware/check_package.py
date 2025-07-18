from django.shortcuts import redirect
from django.urls import reverse

class PackageCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            exempt_paths = [
                reverse('packages:package_list'),
                reverse('auth_login'),
                reverse('logout'),
            ]
            if not user.is_superuser and request.path not in exempt_paths:
                if not hasattr(user, 'userpackage') or not user.userpackage.is_active:
                    return redirect('packages:package_list')
        return self.get_response(request)
