from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
import numpy as np

def roll_die() -> int:
    """Return the value of a rolled dice"""
    value = np.random.randint(1, 7)
    return {"status": "success", "value":value}


root_agent = Agent(
    model=LiteLlm(model="ollama_chat/qwen2.5:latest"),
    name="dice_agent",
    description=(
        "hello world agent that can roll a dice of 6 sides"
    ),
    instruction="""
      You roll dice and tell the outcome of the dice.
    """,
    tools=[
        roll_die,
    ],
)