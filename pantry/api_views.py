
from rest_framework.decorators import (
    api_view,
    authentication_classes,
)
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
)
from rest_framework.response import Response
from rest_framework import status

from django.db.models import Q

from .models import PantryItem
from .serializers import PantryItemSerializer


@api_view(["GET", "POST"])
@authentication_classes([
    SessionAuthentication,
    BasicAuthentication,
])
def pantry_api_list(request):

    # Pastikan user sudah login
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # GET: Mengambil daftar pantry milik user
    if request.method == "GET":

        items = PantryItem.objects.filter(
            user=request.user
        )

        # Search berdasarkan nama bahan
        search = request.query_params.get("search")

        if search:
            items = items.filter(
                name__icontains=search
            )

        # Filter berdasarkan kategori
        category = request.query_params.get("category")

        if category:
            items = items.filter(
                category__iexact=category.strip()
            )

        # Sorting berdasarkan tanggal kedaluwarsa
        sort = request.query_params.get("sort")

        if sort == "expiry":
            items = items.order_by("expiry_date", "name")
        elif sort == "name":
            items = items.order_by("name")

        serializer = PantryItemSerializer(
            items,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # POST: Menambahkan bahan baru
    elif request.method == "POST":

        serializer = PantryItemSerializer(
            data=request.data
        )

        if serializer.is_valid():
            serializer.save(user=request.user)

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@authentication_classes([
    SessionAuthentication,
    BasicAuthentication,
])
def pantry_api_detail(request, pk):

    # Pastikan user sudah login
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Cari item yang dimiliki oleh user
    try:
        item = PantryItem.objects.get(
            pk=pk,
            user=request.user
        )

    except PantryItem.DoesNotExist:
        return Response(
            {"error": "Pantry item not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # GET: Mengambil detail bahan
    if request.method == "GET":

        serializer = PantryItemSerializer(item)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # PUT/PATCH: Mengedit bahan
    elif request.method in ["PUT", "PATCH"]:

        serializer = PantryItemSerializer(
            item,
            data=request.data,
            partial=(request.method == "PATCH")
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # DELETE: Menghapus bahan
    elif request.method == "DELETE":

        item.delete()

        return Response(
            {"message": "Pantry item deleted successfully."},
            status=status.HTTP_200_OK
        )
