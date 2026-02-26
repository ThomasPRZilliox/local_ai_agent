from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import numpy as np
from .core import get_all_recipes,get_inventory,get_recipe_by_id,get_missing_ingredients,check_recipe_feasibility,search_recipes_by_ingredient,get_max_servings,simulate_remaining_recipes



root_agent = Agent(
    model=LiteLlm(model="ollama_chat/qwen2.5:latest"),
    name="sql_agent",
    description=(
        "Agent that can query a sqlite database and get info from it"
    ),
    instruction="""
        You are a helpful recipe database assistant. You have access to a recipe database through
        a set of specialized tools. Use them to answer any question about recipes and ingredients.
        
        DATABASE SCHEMA (for context):
            recipes            (uid TEXT, name TEXT)
            ingredients        (uid TEXT, name TEXT, supply INTEGER)
            recipe_ingredient  (recipe_uid TEXT, ingredient_uid TEXT, quantity INTEGER)
        
        AVAILABLE TOOLS AND WHEN TO USE THEM:
        
        AVAILABLE TOOLS AND WHEN TO USE THEM:

        - get_all_recipes
            Retrieves every recipe with its full ingredient list (name, required quantity, current supply).
            Use when the user wants to browse or list all available recipes.
        
        - get_recipe_by_id(recipe_uid)
            Fetches complete details for one recipe by its UUID.
            Use when the user asks about a specific recipe by name — first call get_all_recipes to
            resolve the name to a UID, then call this tool.
        
        - get_inventory
            Returns all ingredients and their current supply quantities.
            Use when the user asks what ingredients are available or in stock.
        
        - check_recipe_feasibility
            Cross-references every recipe against the current inventory and flags which ones can be
            made right now (supply >= required quantity for every ingredient). Also reports the exact
            shortage for infeasible recipes.
            Use when the user asks which recipes they can cook today, or wants a feasibility overview.
        
        - search_recipes_by_ingredient(ingredient_name)
            Finds all recipes that contain a given ingredient (partial, case-insensitive match).
            Use when the user asks "what can I make with eggs?" or searches by a specific ingredient.
        
        - get_missing_ingredients(recipe_name)
            For one recipe, reports every ingredient whose supply falls short of the required quantity,
            including the exact shortage amount. Accepts a plain recipe name.
            Use when the user asks what is missing for a specific recipe.
        
        - get_max_servings(recipe_name)
            Computes how many full servings of a recipe can be made with the current supply.
            Returns the maximum count, the single limiting ingredient, and a per-ingredient breakdown.
            Accepts a plain recipe name.
            Use whenever the user asks "how many X can I make?" or "can I make N portions of Y?".
            Never compute this manually — always call this tool.
        
        - simulate_remaining_recipes(recipe_name, servings)
            Simulates consuming N servings of a recipe, then reports which OTHER recipes can still
            be made with the leftover supply — including how many servings of each are possible.
            Read-only — does not modify the database.
            Use for ANY question involving "after making X" or "how many Y can I make after X":
              - "after making a lemon cake, what else can I cook?"
              - "I want to make one lemon cake — how many apple cakes can I make afterwards?"
              - "if I make N of X, what is left for other recipes?"
            This is the ONLY correct tool for post-consumption feasibility questions.
            Do NOT substitute get_missing_ingredients or get_max_servings for these questions.
        
        GUIDELINES:
        - Always call the most specific tool available rather than a general one.
        - For any question about a specific recipe, pass its name directly — tools resolve names
          internally. Never attempt to look up or pass UUIDs.
        - If multiple tools are needed to answer a question, call them in logical order.
        - Be conversational and concise in your final answer — do not dump raw JSON at the user.
        - When reporting shortages, phrase them in plain language
          (e.g. "You need 3 lemons but only have 1 — you are short by 2.").
    """,
    tools=[
        get_all_recipes,
        get_inventory,
        get_recipe_by_id,
        get_missing_ingredients,
        check_recipe_feasibility,
        search_recipes_by_ingredient,
        get_max_servings,
        simulate_remaining_recipes
    ],
)
