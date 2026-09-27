from django.db import models

# Create your models here.

# menyimpan informasi resep
class Recipe(models.Model):
    mealdb_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    alternate_name = models.CharField(max_length=200, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    tags = models.CharField(max_length=500, blank=True, null=True)
    source_url = models.URLField(blank=True, null=True)
    image_source = models.URLField(blank=True, null=True)
    creative_commons_confirmed = models.CharField(max_length=10, blank=True, null=True)
    date_modified = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name

# menyimpan daftar bahan secara unik
class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

#class yang menghubungkan recipe dengan ingredient karena 1 resep bisa punya banyak bahan
# dan 1 bahan bisa punya banyak resep
# class ini untuk menyimpan ukuran juga dari masing-masing bahan
class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="recipe_ingredients")
    measure = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["recipe", "ingredient"], name="unique_recipe_ingredient")
        ]

        def __str__(self):
            return f"{self.recipe.name} - {self.ingredient.name}"


    


