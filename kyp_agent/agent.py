from google.adk.agents import SequentialAgent
from .sub_agents import (
    credit_analyzer,
    ratio_calculator,
    report_generator
)
root_agent = SequentialAgent(
    name="KYPOrchestrator",
    sub_agents=[credit_analyzer, ratio_calculator, report_generator],
    description=(
    "Sequential workflow for end-to-end KYP credit analysis. "
    "Accepts raw 'duplicata' data and executes a strict pipeline: "
    "Credit Analysis -> Ratio Calculation -> Final Markdown Report."
)
)