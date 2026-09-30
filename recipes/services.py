import requests

from .models import Recipe, Ingredient, RecipeIngredient


THEMEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"


def import_recipe_from_themealdb(meal_id):
    url = f"{THEMEALDB_BASE_URL}/lookup.php"
    response = requests.get(
        url,
        params={"i": meal_id},
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("meals"):
        return None

    meal = data["meals"][0]

    recipe, created = Recipe.objects.update_or_create(
        mealdb_id=meal["idMeal"],
        defaults={
            "name": meal["strMeal"],
            "alternate_name": meal["strMealAlternate"],
            "category": meal["strCategory"],
            "area": meal["strArea"],
            "country": meal["strCountry"],
            "instructions": meal["strInstructions"],
            "image_url": meal["strMealThumb"],
            "youtube_url": meal["strYoutube"],
            "tags": meal["strTags"],
            "source_url": meal["strSource"],
            "image_source": meal["strImageSource"],
            "creative_commons_confirmed": meal["strCreativeCommonsConfirmed"],
        }
    )

    # Memasukkan ingredient dan measure
    for i in range(1, 21):
        ingredient_name = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")

        # Abaikan ingredient yang kosong
        if not ingredient_name or not ingredient_name.strip():
            continue

        ingredient_name = ingredient_name.strip()

        ingredient, _ = Ingredient.objects.get_or_create(
            name=ingredient_name
        )

        RecipeIngredient.objects.update_or_create(
            recipe=recipe,
            ingredient=ingredient,
            defaults={
                "measure": (measure or "").strip()
            }
        )

    return recipe

def get_meal_ids_by_letter(letter):
    url = f"{THEMEALDB_BASE_URL}/search.php"

    response = requests.get(url, params={"f":letter}, timeout=10)
    response.raise_for_status()

    data = response.json()
    if not data.get("meals"):
        return []
    
    return [meal["idMeal"] for meal in data["meals"]]