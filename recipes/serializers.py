
from rest_framework import serializers
from django.db import transaction

from .models import Recipe, Ingredient, RecipeIngredient



class RecipeIngredientSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    measure = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    def to_representation(self, instance):
        return {
            "name": instance.ingredient.name,
            "measure": instance.measure
        }



class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        source="recipe_ingredients",
        many=True
    )

    class Meta:
        model = Recipe
        fields = [
            "id",
            "mealdb_id",
            "name",
            "alternate_name",
            "category",
            "area",
            "country",
            "instructions",
            "image_url",
            "youtube_url",
            "tags",
            "source_url",
            "image_source",
            "creative_commons_confirmed",
            "date_modified",
            "created_by",
            "ingredients",
        ]
        read_only_fields = [
            "id",
            "mealdb_id",
            "created_by",
        ]

    def validate_ingredients(self, ingredients):
        names = [item["name"].strip().casefold() for item in ingredients]

        if len(names) != len(set(names)):
            raise serializers.ValidationError(
                "Ingredient tidak boleh duplikat."
            )

        return ingredients

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop("recipe_ingredients")

        recipe = Recipe.objects.create(**validated_data)

        for item in ingredients_data:
            ingredient, _ = Ingredient.objects.get_or_create(
                name=item["name"].strip()
            )

            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                measure=item.get("measure")
            )

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop(
            "recipe_ingredients",
            None
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()

            for item in ingredients_data:
                ingredient, _ = Ingredient.objects.get_or_create(
                    name=item["name"].strip()
                )

                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    measure=item.get("measure")
                )

        return instance
