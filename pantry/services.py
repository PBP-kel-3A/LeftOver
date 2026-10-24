"""Penghubung Pantry Tracker -> Katalog Resep.

Resep di katalog berasal dari TheMealDB, jadi nama bahannya berbahasa Inggris
(Egg, Carrots, Garlic, ...). Nama bahan di pantry ditulis user dalam bahasa
Indonesia, sehingga perlu diterjemahkan dulu sebelum dipakai sebagai filter
`ingredients` di Katalog Resep (yang memakai `icontains`).
"""

import re
# Kata kunci Indonesia -> kata kunci TheMealDB.
# Dicocokkan per kata utuh; kunci yang lebih panjang dicek lebih dulu,
# jadi "bawang putih" menang atas "bawang", "telur" atas "ayam", dst.
INDONESIAN_TO_MEALDB = {
    # Protein
    "daging ayam": "chicken",
    "ayam": "chicken",
    "telur": "egg",
    "daging sapi": "beef",
    "sapi": "beef",
    "kambing": "lamb",
    "babi": "pork",
    "sosis": "sausage",
    "bacon": "bacon",
    "ikan": "fish",
    "salmon": "salmon",
    "tuna": "tuna",
    "udang": "prawn",
    "cumi": "squid",
    "tahu": "tofu",
    "tempe": "tempeh",
    # Sayur
    "bawang putih": "garlic",
    "bawang merah": "onion",
    "bawang bombay": "onion",
    "bawang": "onion",
    "daun bawang": "spring onion",
    "wortel": "carrot",
    "kentang": "potato",
    "tomat": "tomato",
    "cabai": "chilli",
    "cabe": "chilli",
    "lombok": "chilli",
    "jahe": "ginger",
    "kunyit": "turmeric",
    "bayam": "spinach",
    "brokoli": "broccoli",
    "kubis": "cabbage",
    "kol": "cabbage",
    "jamur": "mushroom",
    "terong": "aubergine",
    "timun": "cucumber",
    "mentimun": "cucumber",
    "jagung": "corn",
    "buncis": "green beans",
    "kacang panjang": "green beans",
    "kacang tanah": "peanut",
    "kacang merah": "kidney beans",
    "labu": "pumpkin",
    "ubi": "sweet potato",
    "singkong": "cassava",
    "selada": "lettuce",
    "seledri": "celery",
    "peterseli": "parsley",
    "tauge": "bean sprouts",
    # Buah
    "jeruk nipis": "lime",
    "jeruk": "orange",
    "lemon": "lemon",
    "apel": "apple",
    "pisang": "banana",
    "mangga": "mango",
    "nanas": "pineapple",
    "alpukat": "avocado",
    # Bahan pokok & bumbu
    "beras": "rice",
    "nasi": "rice",
    "mie": "noodle",
    "pasta": "pasta",
    "spageti": "spaghetti",
    "roti": "bread",
    "tepung terigu": "flour",
    "tepung": "flour",
    "gula": "sugar",
    "garam": "salt",
    "merica": "pepper",
    "lada": "pepper",
    "mentega": "butter",
    "margarin": "butter",
    "susu": "milk",
    "keju": "cheese",
    "yogurt": "yogurt",
    "krim": "cream",
    "minyak zaitun": "olive oil",
    "minyak": "oil",
    "kecap": "soy sauce",
    "santan": "coconut milk",
    "madu": "honey",
    "cuka": "vinegar",
    "kaldu": "stock",
}

# Urutkan dari kunci terpanjang supaya frasa spesifik dicek lebih dulu.
_PATTERNS = [
    (re.compile(rf"\b{re.escape(key)}\b"), value)
    for key, value in sorted(
        INDONESIAN_TO_MEALDB.items(), key=lambda kv: len(kv[0]), reverse=True
    )
]


def to_recipe_keyword(name):
    """Terjemahkan satu nama bahan pantry jadi kata kunci filter resep.

    Kalau tidak ada di kamus (misal user sudah menulis dalam bahasa Inggris),
    nama aslinya dipakai apa adanya.
    """
    normalized = " ".join(name.lower().split())
    for pattern, english in _PATTERNS:
        if pattern.search(normalized):
            return english
    return normalized


def recipe_keywords(items):
    """Daftar kata kunci unik (urutan dipertahankan) dari kumpulan PantryItem."""
    keywords = []
    for item in items:
        keyword = to_recipe_keyword(item.name)
        if keyword and keyword not in keywords:
            keywords.append(keyword)
    return keywords
