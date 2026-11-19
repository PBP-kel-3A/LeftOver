
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from .models import Recipe
from .serializers import RecipeSerializer



@api_view(["GET", "POST"])
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
        serializer = RecipeSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(
                created_by=request.user
                if request.user.is_authenticated else None
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )



@api_view(["GET"])
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

    serializer = RecipeSerializer(recipe)

    return Response(
        serializer.data,
        status=status.HTTP_200_OK
    )
