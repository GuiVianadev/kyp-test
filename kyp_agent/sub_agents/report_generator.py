from google.adk.agents import Agent
from ..tools import generate_complete_report
from . import report_generator_prompt
report_generator = Agent(
    name="report_generator",
    model= "gemini-2.5-flash",
    description=(
        "Professional report writer specialized in credit analysis documentation"
    ),
    tools=[generate_complete_report],
    instruction= report_generator_prompt.REPORT_GENERATOR_PROMPT,
    output_key="final_report"
)