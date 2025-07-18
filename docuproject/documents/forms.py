from django import forms
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        exclude = ['owner', 'file_type', 'size', 'uploaded_at', 'updated_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Document title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. invoice, travel, pdf'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HR, Finance'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pull user from kwargs
        super().__init__(*args, **kwargs)

        # Hide department field if not an employee
        if not user or user.user_type != 'employee':
            self.fields['department'].widget = forms.HiddenInput()
