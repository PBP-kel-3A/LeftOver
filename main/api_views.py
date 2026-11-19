from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(["POST"])
@permission_classes([AllowAny])
def login_api(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(request, username=username, password=password)
    if user is not None:
        if user.is_active:
            auth_login(request, user)
            return Response(
                {
                    "status": True,
                    "message": "Login berhasil!",
                    "username": user.username,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"status": False, "message": "Akun dinonaktifkan."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response(
        {"status": False, "message": "Username atau password salah."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def register_api(request):
    username = request.data.get("username")
    password = request.data.get("password")
    password2 = request.data.get("password2")

    if not username or not password:
        return Response(
            {"status": False, "message": "Username dan password wajib diisi."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password2 is not None and password != password2:
        return Response(
            {"status": False, "message": "Konfirmasi password tidak cocok."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"status": False, "message": "Username sudah digunakan."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(username=username, password=password)
    return Response(
        {
            "status": True,
            "message": "Akun berhasil dibuat!",
            "username": user.username,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_api(request):
    username = request.user.username
    auth_logout(request)
    return Response(
        {
            "status": True,
            "message": "Logout berhasil!",
            "username": username,
        },
        status=status.HTTP_200_OK,
    )