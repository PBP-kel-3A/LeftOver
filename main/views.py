from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

# Create your views here.
def landing(request):
    return render(request, "main/landing.html")

# Code untuk register
def register_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('main:login')
    else:
        form = UserCreationForm()
    
    context = {'form': form}
    return render(request, 'register.html', context)

# Code untuk login user
def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('main:landing')
        else:
            messages.error(request, "Username atau password salah.")
    else:
        form = AuthenticationForm(request)
    
    context = {
        'form': form
        }
    return render(request, 'login.html', context)

def logout_user(request):
    auth_logout(request)
    return redirect('main:landing')