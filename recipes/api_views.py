from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework import status
from django.db.models import Q

from .models import Recipe
from .serializers import RecipeSerializer



@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication, BasicAuthentication,])
def recipe_api_list(request):
    if request.method == "GET":
        recipes = Recipe.objects.prefetch_related(
            "recipe_ingredients__ingredient"
        )

        # Search berdasarkan nama, kategori, atau area
        search = request.query_params.get("search")

        if search:
            recipes = recipes.filter(
                Q(name__icontains=search) |
                Q(category__icontains=search) |
                Q(area__icontains=search)
            )

        # Filter berdasarkan kategori
        category = request.query_params.get("category")

        if category:
            recipes = recipes.filter(
                category__iexact=category.strip()
            )

        # Filter berdasarkan semua bahan yang diminta
        ingredients = request.query_params.get("ingredients")

        if ingredients:
            ingredient_names = [
                name.strip()
                for name in ingredients.split(",")
                if name.strip()
            ]

            for ingredient_name in ingredient_names:
                recipes = recipes.filter(
                    recipe_ingredients__ingredient__name__iexact=ingredient_name
                )

        recipes = recipes.distinct().order_by("name")

        serializer = RecipeSerializer(recipes, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    elif request.method == "POST":
        if not request.user.is_authenticated:
            return Response({"error" : "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = RecipeSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(created_by=request.user)

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )




@api_view(["GET", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication, BasicAuthentication,])
def recipe_api_detail(request, pk):
    try:
        recipe = Recipe.objects.prefetch_related(
            "recipe_ingredients__ingredient"
        ).get(pk=pk)

    except Recipe.DoesNotExist:
        return Response(
            {"error": "Recipe not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # READ: Semua pengguna dapat melihat resep
    if request.method == "GET":
        serializer = RecipeSerializer(recipe)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # UPDATE dan DELETE: Hanya staff atau superuser
    if request.method in ["PUT", "PATCH", "DELETE"]:
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "You do not have permission to modify recipes."},
                status=status.HTTP_403_FORBIDDEN
            )

    # UPDATE: PUT dan PATCH
    if request.method in ["PUT", "PATCH"]:
        serializer = RecipeSerializer(
            recipe,
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

    # DELETE
    elif request.method == "DELETE":
        recipe.delete()

        return Response(
            {"message": "Recipe deleted successfully."},
            status=status.HTTP_200_OK
        )

