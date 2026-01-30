from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate
from .models import CustomUser
class UserRegistrationForm(UserCreationForm):
    # Additional fields from your registration form
    email = forms.EmailField(
        max_length=254, 
        help_text='Required. Enter a valid email address.',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Primary email address',
            'id': 'email1'
        })
    )   
    email2 = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Secondary email (optional)',
            'id': 'email2'
        })
    )
    
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name',
            'id': 'firstName'
        })
    )
    
    middle_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter middle name (optional)',
            'id': 'middleName'
        })
    )
    
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name',
            'id': 'lastName'
        })
    )
    
    company_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your company ID',
            'id': 'companyId'
        })
    )
    
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create password',
            'id': 'password'
        })
    )
    
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'id': 'confirmPassword'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('email', 'email2', 'first_name', 'middle_name', 'last_name', 
                  'company_id', 'password1', 'password2')
    
    def clean_email2(self):
        email2 = self.cleaned_data.get('email2')
        email1 = self.cleaned_data.get('email')
        
        if email2 and email2 == email1:
            raise forms.ValidationError("Secondary email must be different from primary email.")
        
        if email2:
            if CustomUser.objects.filter(email=email2).exists():
                raise forms.ValidationError("This email is already registered.")
        
        return email2

class UserLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'id': 'loginEmail'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'id': 'loginPassword'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'rememberMe'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
        
        return cleaned_data