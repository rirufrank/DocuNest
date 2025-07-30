from django.shortcuts import render

def privacy_policy(request):
    return render(request, 'resources/privacy_policy.html')

def data_protection_policy(request):
    return render(request, 'resources/data_protection.html')

def terms_and_conditions(request):
    return render(request, 'resources/terms_and_conditions.html')
