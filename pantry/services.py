"""Bridge between the Pantry Tracker and the Recipe Catalog.

Recipes in the catalog come from TheMealDB, so ingredient names there are in
English and follow TheMealDB's wording (Eggs, Carrots, Spring Onions, ...).
The catalog's `ingredients` filter uses `icontains`.

For one pantry ingredient, the keyword sent to the catalog is the first of
these guesses that really exists in the catalog:

1. the "Recipe Catalog Name" the user set in the edit dialog. It is used
   as-is; if it isn't in the catalog the ingredient is skipped.
2. an IngredientAlias row (managed in the Django admin)
3. the ingredient name as typed (also tried in singular form)
4. the name with built-in synonyms applied (eggplant -> aubergine)

Ingredients without a match are skipped and the user is told, so one unknown
ingredient cannot empty the whole search (the catalog filter is an AND).
"""
import re
from dataclasses import dataclass, field

from recipes.models import RecipeIngredient

from .models import IngredientAlias

# What people type -> how TheMealDB usually words it. Keys are singular (a
# trailing "s" is matched automatically) and are replaced inside the name, so
# "Chili Powder" becomes "chilli powder". Best effort: a synonym that isn't in
# the catalog is simply ignored.
SYNONYMS = {
    "eggplant": "aubergine",
    "zucchini": "courgette",
    "cilantro": "coriander",
    "scallion": "spring onion",
    "green onion": "spring onion",
    "shrimp": "prawn",
    "ground beef": "minced beef",
    "heavy whipping cream": "double cream",
    "heavy cream": "double cream",
    "arugula": "rocket",
    "powdered sugar": "icing sugar",
    "confectioners sugar": "icing sugar",
    "all-purpose flour": "plain flour",
    "all purpose flour": "plain flour",
    "yogurt": "yoghurt",
    "garbanzo bean": "chickpea",
    "fava bean": "broad bean",
    "beet": "beetroot",
    "rutabaga": "swede",
    "baking soda": "bicarbonate of soda",
    "chili": "chilli",
}


def _compile(mapping):
    """(regex, replacement) pairs, longest key first so
    "heavy whipping cream" wins over "heavy cream"."""
    return [
        (re.compile(rf"\b{re.escape(key)}s?\b"), value)
        for key, value in sorted(
            mapping.items(), key=lambda kv: len(kv[0]), reverse=True
        )
    ]


_SYNONYM_PATTERNS = _compile(SYNONYMS)


def _normalize(text):
    return " ".join(text.lower().split())


def apply_synonyms(name):
    """Rewrite common wording into TheMealDB's: 'Eggplant' -> 'aubergine'."""
    result = _normalize(name)
    for pattern, replacement in _SYNONYM_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _alias_keyword(name, patterns):
    for pattern, keyword in patterns:
        if pattern.search(name):
            return keyword
    return None


def catalog_ingredient_names():
    """Ingredient names that recipes in the catalog really use (A-Z)."""
    return list(
        RecipeIngredient.objects
        .order_by("ingredient__name")
        .values_list("ingredient__name", flat=True)
        .distinct()
    )


@dataclass
class KeywordResult:
    keywords: list = field(default_factory=list)  # keywords to send to the catalog
    skipped: list = field(default_factory=list)   # pantry names that had no match
    catalog_empty: bool = False                   # no recipes imported yet


def _candidates(keyword):
    # "carrots" is also tried as "carrot" (the catalog may use the singular)
    candidates = [keyword]
    if len(keyword) > 3 and keyword.endswith("s"):
        candidates.append(keyword[:-1])
    return candidates


def resolve_recipe_keywords(items):
    """Work out catalog keywords for a collection of PantryItem.

    Returns a KeywordResult: the valid keywords (unique, order kept) and the
    pantry names that were skipped because the catalog doesn't know them.
    """
    catalog = [name.lower() for name in catalog_ingredient_names()]
    result = KeywordResult(catalog_empty=not catalog)

    if not catalog:
        result.skipped = list(dict.fromkeys(item.name for item in items))
        return result

    aliases = dict(IngredientAlias.objects.values_list("alias", "keyword"))
    alias_patterns = _compile(aliases) if aliases else []

    for item in items:
        name = _normalize(item.name)
        override = _normalize(item.recipe_name)

        if override:
            guesses = [override]
        else:
            guesses = [
                _alias_keyword(name, alias_patterns),
                name,
                apply_synonyms(name),
            ]
        guesses = [guess for guess in dict.fromkeys(guesses) if guess]

        match = next(
            (
                candidate
                for guess in guesses
                for candidate in _candidates(guess)
                if any(candidate in catalog_name for catalog_name in catalog)
            ),
            None,
        )

        if match:
            if match not in result.keywords:
                result.keywords.append(match)
        elif item.name not in result.skipped:
            result.skipped.append(item.name)

    return result
