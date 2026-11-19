from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Review
from .serializers import ReviewSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticatedOrReadOnly])
def review_api_list(request):
    if request.method == "GET":
        reviews = Review.objects.all()
        recipe_id = request.query_params.get("recipe")
        if recipe_id:
            reviews = reviews.filter(recipe_id=recipe_id)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def review_api_detail(request, pk):
    review = get_object_or_404(Review, pk=pk)

    if request.method == "GET":
        serializer = ReviewSerializer(review)
        return Response(serializer.data)

    # memastikan hanya pemilik review yang bisa edit/hapus
    if review.user != request.user:
        return Response(
            {"detail": "Anda tidak memiliki izin untuk mengubah ulasan ini."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method in ["PUT", "PATCH"]:
        serializer = ReviewSerializer(
            review, data=request.data, partial=(request.method == "PATCH")
        )
        if serializer.is_valid():
            serializer.save(is_edited=True)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)