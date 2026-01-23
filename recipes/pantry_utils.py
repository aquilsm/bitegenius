import re
from difflib import get_close_matches

# Simple alias map (we’ll expand later)
INGREDIENT_ALIASES = {
    "capsicum": "bell pepper",
    "chillies": "chili",
    "chilli": "chili",
    "tomatoes": "tomato",
    "potatoes": "potato",
}

def normalize_ingredient(name: str) -> str:
    """
    Normalize ingredient names for consistent matching.
    """
    if not name:
        return ""

    name = name.strip().lower()

    # Remove extra spaces
    name = re.sub(r"\s+", " ", name)

    # Basic plural handling
    if name.endswith("es"):
        name = name[:-2]
    elif name.endswith("s"):
        name = name[:-1]

    # Alias mapping
    return INGREDIENT_ALIASES.get(name, name)

def fuzzy_match_ingredient(name, known_ingredients, cutoff=0.8):
    """
    Try to fuzzy-match an ingredient name against known ingredients.
    Returns best match or original name.
    """
    matches = get_close_matches(
        name,
        known_ingredients,
        n=1,
        cutoff=cutoff
    )
    return matches[0] if matches else name