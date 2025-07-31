# accounts/forms.py
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.db import models
from django.contrib.auth.forms import UserCreationForm
from django.forms.utils import ErrorList
from .models import CustomUser, IndividualProfile, CompanyProfile, EmployeeProfile, Department
from django.forms.widgets import ClearableFileInput

class CustomFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
           
class IndividualRegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=20)
    gender = forms.ChoiceField(choices=[('male', 'Male'), ('female', 'Female')])
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ['email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'individual'
        if commit:
            user.save()
            IndividualProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                phone=self.cleaned_data['phone'],
                gender=self.cleaned_data['gender'],
                profile_picture=self.cleaned_data.get('profile_picture')
            )
        return user

class CompanyAdminRegistrationForm(UserCreationForm):
    company_name = forms.CharField(max_length=255)
    company_email = forms.EmailField()
    company_phone = forms.CharField(max_length=20)
    company_website = forms.URLField(required=False)
    company_logo = forms.ImageField(required=False)
    address = forms.CharField(max_length=255)
    city = forms.CharField(max_length=100)
    country = forms.CharField(max_length=100)
    admin_full_name = forms.CharField(max_length=100)
    admin_phone = forms.CharField(max_length=20)
    industry = forms.CharField(max_length=100, required=False)

    class Meta:
        model = CustomUser
        fields = ['email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'company'
        if commit:
            user.save()
            CompanyProfile.objects.create(
                user=user,
                company_name=self.cleaned_data['company_name'],
                company_email=self.cleaned_data['company_email'],
                company_phone=self.cleaned_data['company_phone'],
                company_website=self.cleaned_data.get('company_website'),
                company_logo=self.cleaned_data.get('company_logo'),
                address=self.cleaned_data['address'],
                city=self.cleaned_data['city'],
                country=self.cleaned_data['country'],
                admin_full_name=self.cleaned_data['admin_full_name'],
                admin_phone=self.cleaned_data['admin_phone'],
                industry=self.cleaned_data.get('industry'),
            )
        return user

class EmployeeRegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=255)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    gender = forms.ChoiceField(choices=[('male', 'Male'), ('female', 'Female')], required=False)
    profile_picture = forms.ImageField(required=False)
    employee_code = forms.CharField(max_length=50, required=False)
    company = forms.ModelChoiceField(queryset=CustomUser.objects.filter(user_type='company'))

    class Meta:
        model = CustomUser
        fields = ['email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'employee'
        if commit:
            user.save()
            EmployeeProfile.objects.create(
                user=user,
                company=self.cleaned_data['company'],
                full_name=self.cleaned_data['full_name'],
                email=self.cleaned_data['email'],
                phone=self.cleaned_data['phone'],
                gender=self.cleaned_data.get('gender'),
                profile_picture=self.cleaned_data.get('profile_picture'),
                employee_code=self.cleaned_data.get('employee_code'),
            )
        return user

class LoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Email',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password',
    }))

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department name'})
        }

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = ['full_name', 'phone', 'employee_code', 'department']

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            'company_name',
            'company_phone',
            'company_website',
            'admin_full_name',
            'admin_phone',
            'address',
        ]
        exclude = ['company_logo']
        
class CompanyLogoForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ['company_logo']
        widgets = {
            'company_logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
