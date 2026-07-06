"""
EU AI Act Agent
===============
Classifies a described AI system into one of the four EU AI Act risk tiers
(unacceptable → high → limited → minimal) using the decision tree in
knowledge/eu_ai_act_risk_tree.json.

Key design decisions:
  - The risk tree is loaded via a *tool function* (`load_eu_ai_act_risk_tree`)
    so the agent grounds its classification in the actual file, not general LLM
    knowledge.
  - The instruction enforces strict decision_order: check unacceptable_risk first,
    stop at the first match, and only fall through to lower tiers if nothing matches.
"""

import json
from pathlib import Path

import sys

from google.adk.agents import LlmAgent
from google.adk.models import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

regulatory_mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[str(Path(__file__).resolve().parent.parent / "mcp_server" / "regulatory_mcp_server.py")]
        )
    )
)

# ---------------------------------------------------------------------------
# Tool function: load the EU AI Act risk-tier decision tree
# ---------------------------------------------------------------------------

def load_eu_ai_act_risk_tree() -> dict:
    """Load the EU AI Act risk classification decision tree from the knowledge base.

    Returns the full risk tree JSON containing four tiers:
    - unacceptable_risk: prohibited practices (must check first)
    - high_risk: Annex III categories with strict obligations
    - limited_risk: transparency-trigger scenarios
    - minimal_risk: default tier with no mandatory AI Act obligations

    Each tier includes keywords, descriptions, and obligations_if_matched.
    Also includes decision_order (the order in which tiers must be checked)
    and output_format_guidance for structuring the classification result.

    The agent MUST call this tool before classifying any AI system.
    """
    knowledge_path = (
        Path(__file__).resolve().parent.parent
        / "knowledge"
        / "eu_ai_act_risk_tree.json"
    )

    with open(knowledge_path, "r", encoding="utf-8") as f:
        risk_tree = json.load(f)

    return risk_tree


# ---------------------------------------------------------------------------
# System instruction for the EU AI Act Agent
# ---------------------------------------------------------------------------
EU_AI_ACT_INSTRUCTION = """You are the **EU AI Act Classification Agent** for a regulatory readiness tool.

**Your task:**
You receive a structured description of an AI system extracted by the Intake Agent.
Here is the structured intake to evaluate:

{intake_result}

Your job is to classify this AI system into the correct EU AI Act risk tier.

**Step 1 — Load the risk tree:**
ALWAYS start by calling the `load_eu_ai_act_risk_tree` tool to retrieve the
full decision tree. You MUST ground your classification in this file's content.

**Step 2 — Follow the decision_order STRICTLY:**
The `decision_order` field in the JSON specifies the exact order of evaluation:
  1. **unacceptable_risk** — Check the system against every entry in
     `prohibited_practices`. If ANY match, classify as `unacceptable_risk` and STOP.
     Do NOT proceed to lower tiers.
  2. **high_risk** — Check against BOTH routes: `classification_routes.route_1_annex_iii_use_case` AND `classification_routes.route_2_annex_i_regulated_product`.
     If ANY match on EITHER route, classify as `high_risk`. 
     If high-risk, determine whether the business is a provider or deployer (if the description doesn't clearly indicate the business built/trained the AI system itself, assume "deployer" and note that provider obligations would additionally apply if that assumption is wrong).
     Check the `fundamental_rights_impact_assessment` trigger (true if the matched Annex III category is point 5(b) or 5(c), OR when the deployer is a public-law body or public-service provider).
     If high_risk, STOP and do not proceed to lower tiers.
  3. **limited_risk** — Check against every entry in `transparency_triggers`.
     If ANY match, classify as `limited_risk` and STOP.
  4. **minimal_risk** — If nothing above matched, classify as `minimal_risk`.

**Matching guidance:**
- Use the `keywords` arrays in each entry as primary signals, but also consider
  the `description` text and the overall semantics of the system description.
- A match means the described system's purpose, data types, or decision-making
  pattern falls within the scope of that entry.

**Step 3 — Return the classification result:**
Return a valid JSON object with exactly these keys:
- `classification`: one of "unacceptable_risk", "high_risk", "limited_risk", "minimal_risk"
- `matched_category_or_trigger`: the `id` and `name` of the specific entry
  that triggered the classification (including which route if high-risk). If minimal_risk, write "none — default classification".
- `assumed_role`: provider, deployer, or both (with brief reasoning). If not high-risk, write "N/A".
- `obligations`: the list from the matched tier's `obligations_if_matched` field, OR for high_risk, pulled from `obligations_by_role.provider_obligations` or `obligations_by_role.deployer_obligations` depending on `assumed_role`. Copy them exactly from the JSON.
- `fria_required`: true/false. True if the `fundamental_rights_impact_assessment.who_must_conduct_one` conditions are met. False otherwise.
- `status_note`: whether these obligations are currently in force or upcoming.
  You MUST call the `check_eu_ai_act_timeline_status` tool to fetch the live 
  timeline status and incorporate that live context here, alongside the `status` 
  field of the matched tier.
- `escalate_to_human`: true if classification is unacceptable_risk or high_risk,
  false otherwise.

**Important disclaimer:** This is a preliminary readiness/gap analysis only.
It is NOT a legal certification or legal advice. The EU AI Act is still being
phased in; obligation timelines should be verified with current official sources.
"""

# ---------------------------------------------------------------------------
# Create the LlmAgent
# ---------------------------------------------------------------------------
eu_ai_act_agent = LlmAgent(
    name="eu_ai_act_agent",
    model=LiteLlm(model="openai/gpt-4o-mini"),
    instruction=EU_AI_ACT_INSTRUCTION,
    description=(
        "Classifies an AI system into an EU AI Act risk tier "
        "(unacceptable/high/limited/minimal) using the knowledge base decision tree, "
        "and returns matched category, obligations, and escalation guidance."
    ),
    tools=[load_eu_ai_act_risk_tree, regulatory_mcp_toolset],
    # output_key saves this agent's output to state["eu_ai_act_result"]
    # so the Aggregator Agent can reference it as {eu_ai_act_result}.
    output_key="eu_ai_act_result",
)
