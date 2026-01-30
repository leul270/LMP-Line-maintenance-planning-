from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
import json
from datetime import datetime
from .models import *
from .forms import UserRegistrationForm, UserLoginForm
from .utils import cookieCart, cartData, guestOrder

def home(request):
    if request.user.is_authenticated:
        return redirect('mycourse')
    return render(request, 'store/home.html')

def indexGen(request):
    context = {}
    return render(request, 'store/indexGen.html', context)

def maintX(request):
    context = {}
    return render(request, 'store/maintX.html', context)
def create_course(request):
    context = {}
    return render(request, 'store/create_course.html', context)

@login_required
def mycourse(request):
    courses = Course.objects.filter(user=request.user)
    
    if not courses.exists():
        # Create a default course for new users
        Course.objects.create(
            user=request.user,
            course_name="Introduction Course",
            description="Welcome to your learning journey! This is your first course.",
            last_completed_date=timezone.now().date(),
            interval_days=30,
            due_date=timezone.now().date() + timedelta(days=30),
            status='active'
        )
        courses = Course.objects.filter(user=request.user)
    
    context = {'courses': courses}
    return render(request, 'store/store.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('mycourse')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                
                # Handle "remember me" functionality
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                
                # Redirect to next page if provided, otherwise to mycourse
                next_page = request.GET.get('next', 'mycourse')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserLoginForm()
    
    return render(request, 'store/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('mycourse')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Save user
            user = form.save(commit=False)
            
            # Handle email2 field (since it's not in UserCreationForm by default)
            email2 = form.cleaned_data.get('email2', '')
            if email2:
                user.email2 = email2
            
            user.save()
            
            # Log the user in
            login(request, user)
            
            # Show success message
            messages.success(request, 'Registration successful! Welcome to your account.')
            
            # Redirect to mycourse page
            return redirect('mycourse')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'store/login.html', {'register_form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

# API view for AJAX registration (optional)
@csrf_exempt
def register_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['firstName', 'lastName', 'email1', 'companyId', 'password']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'message': f'{field} is required.'
                    }, status=400)
            
            # Check if email already exists
            if CustomUser.objects.filter(email=data['email1']).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Email is already registered.'
                }, status=400)
            
            # Check if emails match
            email2 = data.get('email2')
            if email2 and email2 == data['email1']:
                return JsonResponse({
                    'success': False,
                    'message': 'Secondary email must be different from primary email.'
                }, status=400)
            
            # Check password match
            if data['password'] != data.get('confirmPassword'):
                return JsonResponse({
                    'success': False,
                    'message': 'Passwords do not match.'
                }, status=400)
            
            # Check password length
            if len(data['password']) < 8:
                return JsonResponse({
                    'success': False,
                    'message': 'Password must be at least 8 characters.'
                }, status=400)
            
            # Create user
            user = CustomUser.objects.create_user(
                email=data['email1'],
                password=data['password'],
                first_name=data['firstName'],
                middle_name=data.get('middleName', ''),
                last_name=data['lastName'],
                company_id=data['companyId'],
                email2=email2
            )
            
            # Log the user in
            login(request, user)
            
            return JsonResponse({
                'success': True,
                'message': 'Registration successful!',
                'redirect': '/mycourse/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    }, status=405)

# API view for AJAX login (optional)
@csrf_exempt
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return JsonResponse({
                    'success': False,
                    'message': 'Email and password are required.'
                }, status=400)
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Login successful!',
                    'redirect': '/mycourse/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid email or password.'
                }, status=401)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    }, status=405)