import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages

# Landing page view
def landing(request):
    return render(request, "main/landing.html")

# Code untuk register
def register_user(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Account created successfully! Please sign in.")
        return redirect('main:login')
    
    context = {'form': form}
    return render(request, 'register.html', context)

# Code untuk login user
def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        
        # Buat response redirect dan set cookie sesi terakhir login
        response = redirect('main:landing')
        response.set_cookie('last_login', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return response
    
    context = {'form': form}
    return render(request, 'login.html', context)

# Code untuk logout pengguna
def logout_user(request):
    auth_logout(request)
    # Hapus cookie last_login saat logout dan arahkan kembali ke landing page
    response = redirect('main:landing')
    response.delete_cookie('last_login')
    return response