from django.core.management.base import BaseCommand

from recipes.services import (
    get_meal_ids_by_letter,
    import_recipe_from_themealdb,
)


class Command(BaseCommand):
    help = "Import recipes from TheMealDB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--letter",
            type=str,
            default="a",
            help="First letter of recipe names"
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of recipes to import"
        )

    def handle(self, *args, **options):
        letter = options["letter"].lower()
        limit = options["limit"]

        meal_ids = get_meal_ids_by_letter(letter)

        if not meal_ids:
            self.stdout.write(
                self.style.WARNING(
                    f"No recipes found for letter '{letter}'."
                )
            )
            return

        meal_ids = meal_ids[:limit]

        self.stdout.write(
            f"Found {len(meal_ids)} recipes."
        )

        for meal_id in meal_ids:
            self.stdout.write(
                f"Importing meal {meal_id}..."
            )

            recipe = import_recipe_from_themealdb(meal_id)

            if recipe:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully imported: {recipe.name}"
                    )
                )