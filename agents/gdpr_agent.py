"""
GDPR Agent
==========
Evaluates a structured AI-system description (from the Intake Agent) against
the 16 GDPR checkpoints defined in knowledge/gdpr_checklist.json.

Key design decisions:
  - The checklist is loaded via a *tool function* (`load_gdpr_checklist`) rather
    than baked into the instruction. This keeps the instruction readable and
    forces the agent to ground its analysis in the actual file contents.
  - The agent's instruction tells it exactly how to use the tool output and
    what format to return results in.
"""

import json
import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.models import LiteLlm

# ---------------------------------------------------------------------------
# Tool function: load the GDPR checklist from the knowledge base
# ---------------------------------------------------------------------------
# In ADK v2.x, you can pass a plain Python function in the `tools` list and
# ADK will automatically wrap it as a FunctionTool. The function's docstring
# becomes the tool description that the LLM sees, and the LLM decides when
# to call it.

def load_gdpr_checklist() -> dict:
    """Load the GDPR compliance checklist from the knowledge base.

    Returns the full GDPR checklist JSON containing the checkpoints, each with:
    - id, name, article_reference, question, why_it_matters
    - risk_if_missing (high/medium), keywords, guidance_if_flagged
    Also includes output_format_guidance for structuring the evaluation.

    The agent MUST call this tool to retrieve the checklist before evaluating
    any AI system. Do not rely on general knowledge — use this file's content.
    """
    # Build an absolute path to the knowledge file.
    # We go up from agents/ to the project root, then into knowledge/.
    knowledge_path = Path(__file__).resolve().parent.parent / "knowledge" / "gdpr_checklist.json"

    with open(knowledge_path, "r", encoding="utf-8") as f:
        checklist = json.load(f)

    return checklist


# ---------------------------------------------------------------------------
# System instruction for the GDPR Agent
# ---------------------------------------------------------------------------
GDPR_INSTRUCTION = """You are the **GDPR Compliance Agent** for a regulatory readiness tool.

**Your task:**
You receive a structured description of an AI system extracted by the Intake Agent.
Here is the structured intake to evaluate:

{intake_result}

Your job is to evaluate this AI system against the GDPR checklist.

**Step 1 — Load the checklist:**
ALWAYS start by calling the `load_gdpr_checklist` tool to retrieve the full
GDPR checklist. You MUST ground your analysis in the contents of this file.
Do NOT rely on your general knowledge of GDPR — use the checklist.

**Step 2 — Evaluate each checkpoint:**
For EACH of the checkpoints in the checklist, determine:
- `applicable` (true / false): Does this checkpoint apply to the described system?
- `status` ("addressed" / "unaddressed" / "unclear"): Based on the system
  description, is there evidence this requirement is met?
- `risk_if_missing`: Copy the risk level from the checklist (high / medium).
- `rationale`: A one-line explanation of WHY you gave this status.

**Step 3 — Produce an overall summary:**
After all checkpoints, provide:
- `high_risk_unaddressed_count`: Number of checkpoints with risk_if_missing="high"
  that have status="unaddressed" or "unclear"
- `overall_color`:
    - "green" if 0 high-risk gaps
    - "yellow" if there are medium-risk gaps only
    - "red" if 1 or more high-risk gaps
- `summary`: A 2-3 sentence plain-English summary of the key findings.

**Output format:**
Return your evaluation as a valid JSON object with two keys:
1. `checkpoints`: a list of objects (one per checkpoint) with keys:
   checkpoint_id, checkpoint_name, applicable, status, risk_if_missing, rationale
2. `overall`: an object with keys:
   high_risk_unaddressed_count, overall_color, summary

**Important disclaimer:** This is a preliminary readiness/gap analysis only.
It is NOT a legal certification, legal audit, or legal advice. Organizations
should consult qualified legal professionals for binding compliance assessments.
"""

# ---------------------------------------------------------------------------
# Create the LlmAgent
# ---------------------------------------------------------------------------
gdpr_agent = LlmAgent(
    name="gdpr_agent",
    model=LiteLlm(model="openai/gpt-4o-mini"),
    instruction=GDPR_INSTRUCTION,
    description=(
        "Evaluates an AI system description against the GDPR checkpoints "
        "from the knowledge base, returning per-checkpoint status and an "
        "overall compliance readiness color (green/yellow/red)."
    ),
    # Pass the plain function — ADK auto-wraps it as a FunctionTool.
    tools=[load_gdpr_checklist],
    # output_key saves this agent's output to state["gdpr_result"]
    # so the Aggregator Agent can reference it as {gdpr_result}.
    output_key="gdpr_result",
)
