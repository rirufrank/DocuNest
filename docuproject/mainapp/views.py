from django.shortcuts import render

# Create your views here.

def preview_template(request, template_name):
    try:
        return render(request, f"{template_name}.html")
    except:
        return render(request, "dev/not_found.html", {"template": template_name})

def test_view(request):
    return render(request, 'welcome.html')

def homepage(request):
    return render(request, 'homepage.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def welcome(request):
    return render(request, 'welcome.html')