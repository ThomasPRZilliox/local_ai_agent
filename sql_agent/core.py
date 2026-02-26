# import sqlite3
# db_path = r"/Users/thomaszilliox/Documents/git_repos/local_ai_agent/sql_agent/recipes.db"
#
#
#
# def query_database(query: str) -> str:
#     """Execute a SQL query on the recipes database and return results."""
#     try:
#         print(f"Agent ask {query}")
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()
#         cursor.execute(query)
#         results = cursor.fetchall()
#         column_names = [description[0] for description in cursor.description]
#         conn.close()
#
#         if not results:
#             return "No results found."
#
#         # Format results as a readable string
#         formatted_results = []
#         for row in results:
#             row_dict = dict(zip(column_names, row))
#             formatted_results.append(str(row_dict))
#
#         return "\n".join(formatted_results)
#     except Exception as e:
#         return f"Error executing query: {str(e)}"
#
# get_all_recipes():
#     query = """select """
#
#
# if __name__ == "__main__":
#     query = "SELECT name FROM recipes"
#     print(query_database(query))


"""
recipe_tools.py
---------------
Tool implementations for the Recipe Agent, backed by the recipes.db SQLite database.

Database schema:
    recipes            (uid TEXT PK, name TEXT)
    ingredients        (uid TEXT PK, name TEXT, supply INTEGER)
    recipe_ingredient  (recipe_uid TEXT, ingredient_uid TEXT, quantity INTEGER)

Each public function maps 1-to-1 to an Anthropic tool definition (see TOOL_DEFINITIONS).
Pass DB_PATH at import time or override it before calling any function.
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import Any

# ── Configuration ─────────────────────────────────────────────────────────────

# DB_PATH = "recipes.db"  # override as needed, e.g. recipe_tools.DB_PATH = "/path/to/recipes.db"
DB_PATH = r"/Users/thomaszilliox/Documents/git_repos/local_ai_agent/sql_agent/recipes.db"

# ── DB helper ─────────────────────────────────────────────────────────────────

@contextmanager
def _get_conn():
    """Yield a sqlite3 connection with row_factory set to dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]


# ── Tool functions ─────────────────────────────────────────────────────────────
def get_all_recipes() -> list[dict]:
    """
    Return every recipe in the database along with its full ingredient list
    (ingredient name, required quantity, and current supply).

    Returns:
        [
          {
            "uid": "...",
            "name": "lemon cake",
            "ingredients": [
              {"name": "eggs", "quantity": 3, "supply": 10},
              ...
            ]
          },
          ...
        ]
    """
    with _get_conn() as conn:
        recipes = _rows_to_dicts(
            conn.execute("SELECT uid, name FROM recipes ORDER BY name").fetchall()
        )
        for recipe in recipes:
            recipe["ingredients"] = _rows_to_dicts(
                conn.execute(
                    """
                    SELECT i.name, ri.quantity, i.supply
                    FROM recipe_ingredient ri
                    JOIN ingredients i ON i.uid = ri.ingredient_uid
                    WHERE ri.recipe_uid = ?
                    ORDER BY i.name
                    """,
                    (recipe["uid"],),
                ).fetchall()
            )
        return recipes


def get_recipe_by_id(recipe_uid: str) -> dict:
    """
    Return a single recipe by its UID, including its full ingredient list.

    Args:
        recipe_uid: The UUID of the recipe (TEXT primary key).

    Returns:
        {
          "uid": "...",
          "name": "scramble eggs",
          "ingredients": [
            {"name": "eggs", "quantity": 5, "supply": 10}
          ]
        }
        or {"error": "Recipe not found"} if the UID does not exist.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT uid, name FROM recipes WHERE uid = ?", (recipe_uid,)
        ).fetchone()

        if row is None:
            return {"error": f"Recipe '{recipe_uid}' not found."}

        recipe = dict(row)
        recipe["ingredients"] = _rows_to_dicts(
            conn.execute(
                """
                SELECT i.name, ri.quantity, i.supply
                FROM recipe_ingredient ri
                JOIN ingredients i ON i.uid = ri.ingredient_uid
                WHERE ri.recipe_uid = ?
                ORDER BY i.name
                """,
                (recipe_uid,),
            ).fetchall()
        )
        return recipe


def get_inventory() -> list[dict]:
    """
    Return every ingredient in stock with its current supply.

    Returns:
        [
          {"uid": "...", "name": "eggs",  "supply": 10},
          {"uid": "...", "name": "milk",  "supply": 2},
          ...
        ]
    """
    with _get_conn() as conn:
        return _rows_to_dicts(
            conn.execute(
                "SELECT uid, name, supply FROM ingredients ORDER BY name"
            ).fetchall()
        )


def check_recipe_feasibility() -> list[dict]:
    """
    Cross-reference every recipe against the current inventory and report
    which recipes can be made right now.

    A recipe is feasible when every required ingredient has supply >= quantity.

    Returns:
        [
          {
            "recipe_uid":  "...",
            "recipe_name": "apple cake",
            "can_make":    True,
            "missing_ingredients": []          # empty when can_make is True
          },
          {
            "recipe_uid":  "...",
            "recipe_name": "lemon cake",
            "can_make":    False,
            "missing_ingredients": [
              {
                "name":     "lemon",
                "required": 3,
                "in_stock": 1,
                "shortage": 2
              }
            ]
          },
          ...
        ]
    """
    with _get_conn() as conn:
        recipes = _rows_to_dicts(
            conn.execute("SELECT uid, name FROM recipes ORDER BY name").fetchall()
        )
        results = []
        for recipe in recipes:
            rows = _rows_to_dicts(
                conn.execute(
                    """
                    SELECT i.name, ri.quantity, i.supply
                    FROM recipe_ingredient ri
                    JOIN ingredients i ON i.uid = ri.ingredient_uid
                    WHERE ri.recipe_uid = ?
                    """,
                    (recipe["uid"],),
                ).fetchall()
            )
            missing = [
                {
                    "name":     r["name"],
                    "required": r["quantity"],
                    "in_stock": r["supply"],
                    "shortage": r["quantity"] - r["supply"],
                }
                for r in rows
                if r["supply"] < r["quantity"]
            ]
            results.append(
                {
                    "recipe_uid":           recipe["uid"],
                    "recipe_name":          recipe["name"],
                    "can_make":             len(missing) == 0,
                    "missing_ingredients":  missing,
                }
            )
        return results


def search_recipes_by_ingredient(ingredient_name: str) -> list[dict]:
    """
    Find all recipes that contain a given ingredient (case-insensitive partial match).

    Args:
        ingredient_name: Full or partial ingredient name to search for.

    Returns:
        [
          {
            "recipe_uid":           "...",
            "recipe_name":          "lemon cake",
            "matching_ingredient":  "lemon",
            "required_quantity":    3,
            "in_stock":             3
          },
          ...
        ]
    """
    with _get_conn() as conn:
        rows = _rows_to_dicts(
            conn.execute(
                """
                SELECT r.uid  AS recipe_uid,
                       r.name AS recipe_name,
                       i.name AS matching_ingredient,
                       ri.quantity AS required_quantity,
                       i.supply    AS in_stock
                FROM recipe_ingredient ri
                JOIN recipes     r ON r.uid = ri.recipe_uid
                JOIN ingredients i ON i.uid = ri.ingredient_uid
                WHERE LOWER(i.name) LIKE LOWER(?)
                ORDER BY r.name
                """,
                (f"%{ingredient_name}%",),
            ).fetchall()
        )
        return rows


def get_missing_ingredients(recipe_name: str) -> dict:
    """
    For a specific recipe, list every ingredient whose current supply is
    below the required quantity.

    Resolves the recipe by name internally (case-insensitive, partial match)
    so the caller never needs to know the UID.

    Args:
        recipe_name: Full or partial recipe name (e.g. "lemon cake").

    Returns:
        {
          "recipe_uid":   "...",
          "recipe_name":  "lemon cake",
          "can_make":     False,
          "missing_count": 1,
          "missing_ingredients": [
            {"name": "lemon", "required": 3, "in_stock": 1, "shortage": 2}
          ]
        }
        or {"error": "..."} if no matching recipe is found.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT uid, name FROM recipes WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{recipe_name}%",),
        ).fetchone()

        if row is None:
            return {"error": f"No recipe matching '{recipe_name}' found."}

        recipe = dict(row)
        rows = _rows_to_dicts(
            conn.execute(
                """
                SELECT i.name, ri.quantity, i.supply
                FROM recipe_ingredient ri
                JOIN ingredients i ON i.uid = ri.ingredient_uid
                WHERE ri.recipe_uid = ?
                """,
                (recipe["uid"],),
            ).fetchall()
        )
        missing = [
            {
                "name":     r["name"],
                "required": r["quantity"],
                "in_stock": r["supply"],
                "shortage": r["quantity"] - r["supply"],
            }
            for r in rows
            if r["supply"] < r["quantity"]
        ]
        return {
            "recipe_uid":          recipe["uid"],
            "recipe_name":         recipe["name"],
            "can_make":            len(missing) == 0,
            "missing_count":       len(missing),
            "missing_ingredients": missing,
        }


def get_max_servings(recipe_name: str) -> dict:
    """
    Compute how many full servings of a recipe can be made with the current
    ingredient supply, and identify the limiting ingredient.

    Resolves the recipe by name internally (case-insensitive, partial match)
    so the caller never needs to know the UID.

    For each ingredient, the maximum servings it allows is floor(supply / quantity).
    The overall maximum is the minimum across all ingredients.

    Args:
        recipe_name: Full or partial recipe name (e.g. "lemon cake", "lemon").

    Returns:
        {
          "recipe_uid":          "...",
          "recipe_name":         "lemon cake",
          "max_servings":        1,
          "limiting_ingredient": "lemon",
          "breakdown": [
            {"name": "eggs",  "required": 3, "in_stock": 10, "max_servings": 3},
            {"name": "lemon", "required": 3, "in_stock": 3,  "max_servings": 1},
            {"name": "milk",  "required": 1, "in_stock": 2,  "max_servings": 2}
          ]
        }
        or {"error": "..."} if no matching recipe is found.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT uid, name FROM recipes WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{recipe_name}%",),
        ).fetchone()

        if row is None:
            return {"error": f"No recipe matching '{recipe_name}' found."}

        recipe = dict(row)
        rows = _rows_to_dicts(
            conn.execute(
                """
                SELECT i.name, ri.quantity, i.supply
                FROM recipe_ingredient ri
                JOIN ingredients i ON i.uid = ri.ingredient_uid
                WHERE ri.recipe_uid = ?
                ORDER BY i.name
                """,
                (recipe["uid"],),
            ).fetchall()
        )

        if not rows:
            return {"error": f"Recipe '{recipe['name']}' has no ingredients defined."}

        breakdown = [
            {
                "name":         r["name"],
                "required":     r["quantity"],
                "in_stock":     r["supply"],
                "max_servings": r["supply"] // r["quantity"] if r["quantity"] > 0 else 0,
            }
            for r in rows
        ]

        limiting = min(breakdown, key=lambda x: x["max_servings"])

        return {
            "recipe_uid":          recipe["uid"],
            "recipe_name":         recipe["name"],
            "max_servings":        limiting["max_servings"],
            "limiting_ingredient": limiting["name"],
            "breakdown":           breakdown,
        }


def simulate_remaining_recipes(recipe_name: str, servings: int = 1) -> dict:
    """
    Simulate consuming a given number of servings of one recipe, then report
    which OTHER recipes can still be made with the leftover ingredient supply.

    This does NOT modify the database — it is a pure read-only simulation.

    Args:
        recipe_name: Full or partial name of the recipe to consume (e.g. "lemon cake").
        servings:    Number of servings to subtract from the current supply (default: 1).

    Returns:
        {
          "consumed_recipe":  "lemon cake",
          "servings_consumed": 1,
          "remaining_supply": [
            {"name": "eggs",  "before": 10, "used": 3, "after": 7},
            {"name": "lemon", "before": 3,  "used": 3, "after": 0},
            {"name": "milk",  "before": 2,  "used": 1, "after": 1}
          ],
          "feasible_recipes": [
            {
              "recipe_name": "scramble eggs",
              "can_make": True,
              "missing_ingredients": []
            },
            ...
          ]
        }
        or {"error": "..."} if the recipe is not found or servings exceed max_servings.
    """
    with _get_conn() as conn:
        # Resolve recipe by name
        row = conn.execute(
            "SELECT uid, name FROM recipes WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{recipe_name}%",),
        ).fetchone()

        if row is None:
            return {"error": f"No recipe matching '{recipe_name}' found."}

        consumed = dict(row)

        # Get ingredients required for the consumed recipe
        required_rows = _rows_to_dicts(
            conn.execute(
                """
                SELECT i.uid, i.name, ri.quantity, i.supply
                FROM recipe_ingredient ri
                JOIN ingredients i ON i.uid = ri.ingredient_uid
                WHERE ri.recipe_uid = ?
                """,
                (consumed["uid"],),
            ).fetchall()
        )

        # Validate we have enough stock for the requested servings
        for r in required_rows:
            needed = r["quantity"] * servings
            if r["supply"] < needed:
                return {
                    "error": (
                        f"Not enough '{r['name']}' to make {servings} serving(s) of "
                        f"'{consumed['name']}'. Need {needed}, have {r['supply']}."
                    )
                }

        # Build a virtual supply map after consumption
        virtual_supply: dict[str, int] = {
            r["name"]: r["supply"] for r in
            _rows_to_dicts(conn.execute("SELECT name, supply FROM ingredients").fetchall())
        }
        remaining_supply = []
        for r in required_rows:
            used = r["quantity"] * servings
            virtual_supply[r["name"]] -= used
            remaining_supply.append({
                "name":   r["name"],
                "before": r["supply"],
                "used":   used,
                "after":  virtual_supply[r["name"]],
            })

        # Check feasibility of every OTHER recipe against virtual supply
        all_recipes = _rows_to_dicts(
            conn.execute("SELECT uid, name FROM recipes ORDER BY name").fetchall()
        )
        feasible_recipes = []
        for recipe in all_recipes:
            if recipe["uid"] == consumed["uid"]:
                continue  # skip the consumed recipe itself

            ing_rows = _rows_to_dicts(
                conn.execute(
                    """
                    SELECT i.name, ri.quantity
                    FROM recipe_ingredient ri
                    JOIN ingredients i ON i.uid = ri.ingredient_uid
                    WHERE ri.recipe_uid = ?
                    """,
                    (recipe["uid"],),
                ).fetchall()
            )
            missing = [
                {
                    "name":     r["name"],
                    "required": r["quantity"],
                    "in_stock": virtual_supply.get(r["name"], 0),
                    "shortage": r["quantity"] - virtual_supply.get(r["name"], 0),
                }
                for r in ing_rows
                if virtual_supply.get(r["name"], 0) < r["quantity"]
            ]
            feasible_recipes.append({
                "recipe_name":         recipe["name"],
                "can_make":            len(missing) == 0,
                "max_servings":        min(
                    (virtual_supply.get(r["name"], 0) // r["quantity"] if r["quantity"] > 0 else 0)
                    for r in ing_rows
                ) if ing_rows else 0,
                "missing_ingredients": missing,
            })

        return {
            "consumed_recipe":   consumed["name"],
            "servings_consumed": servings,
            "remaining_supply":  remaining_supply,
            "feasible_recipes":  feasible_recipes,
        }