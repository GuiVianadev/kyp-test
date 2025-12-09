from google.adk.agents import Agent
from ..tools import extract_financial_data_tool
from . import credit_analyzer_prompt

credit_analyzer = Agent(
    name="credit_analyzer",
    model= "gemini-2.5-flash",
    description=(
        "Senior credit analyst specialized in extracting financial data "
        "and performing preliminary risk assessment for commercial credit operations"
    ),
    tools=[
        extract_financial_data_tool,
    ],
    instruction= credit_analyzer_prompt.CREDIT_ANALYZER_PROMPT,
    output_key="credit_analysis"
)