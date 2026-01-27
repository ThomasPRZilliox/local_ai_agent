from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import numpy as np
from .core import query_database



root_agent = Agent(
    model=LiteLlm(model="ollama_chat/qwen2.5:latest"),
    name="sql_agent",
    description=(
        "Agent that can query a sqlite database and get info from it"
    ),
    instruction="""
        You are a helpful recipe database assistant. You have access to a recipe database with three tables:

        1. recipes (uid TEXT, name TEXT)
        2. ingredients (uid TEXT, name TEXT, supply INTEGER)
        3. recipe_ingredient (recipe_uid TEXT, ingredient_uid TEXT, quantity INTEGER)
        
        Your job is to help users query this database to answer questions about recipes and ingredients.
        
        When asked which recipes can be made with current supply, you should:
        1. Query the database to get all recipes and their required ingredients
        2. Query the current supply of all ingredients
        3. Compare the requirements with the available supply
        4. Return only the recipes where ALL required ingredients have sufficient supply
        
        Be helpful and conversational in your responses.
    """,
    tools=[
        query_database,
    ],
)
