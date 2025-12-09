from google.adk.agents import Agent
from ..tools import (
    calculate_all_financial_ratios
)
from . import ratio_calculator_prompt
ratio_calculator = Agent(
    name="ratio_calculator",
    model= "gemini-2.5-flash",
 description=(
        "Financial analyst specialized in calculating and interpreting "
        "financial ratios for credit risk assessment"
    ),
    tools=[
       calculate_all_financial_ratios
    ],
    instruction= ratio_calculator_prompt.RATIO_CALCULATOR_PROMPT,
    output_key="financial_ratios"
)