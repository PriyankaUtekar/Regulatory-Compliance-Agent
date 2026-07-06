"""
Aggregator Agent
================
Takes the outputs from both the GDPR Agent and the EU AI Act Agent and
combines them into a single, unified compliance readiness report.

Key responsibilities:
  - Merge findings from both frameworks into one coherent report.
  - Apply the escalation gate: if EITHER framework triggers escalation
    (high-risk GDPR gaps OR EU AI Act escalate_to_human=true), the report
    MUST lead with the human-review warning.
  - Always end with a legal disclaimer regardless of risk level.
"""

from google.adk.agents import LlmAgent
from google.adk.models import LiteLlm

# ---------------------------------------------------------------------------
# System instruction for the Aggregator Agent
# ---------------------------------------------------------------------------
# This instruction references {gdpr_result} and {eu_ai_act_result}, which are
# session state keys populated by the GDPR and EU AI Act agents via their
# output_key settings. ADK automatically substitutes these placeholders with
# the actual agent outputs before the instruction reaches the LLM.
AGGREGATOR_INSTRUCTION = """You are the **Aggregator Agent** for a regulatory compliance readiness tool.

You receive the outputs of three upstream components:

**Intake Agent output (project context):**
{intake_result}

**GDPR Agent output:**
{gdpr_result}

**EU AI Act Agent output:**
{eu_ai_act_result}

---

**Your job:** Combine these evaluations into a single, clear compliance readiness report.

**Escalation Gate Rule:** If either the GDPR Agent output or EU AI Act Agent output contains the text "COULD NOT VERIFY THIS PART OF THE ASSESSMENT", you MUST start the entire report with a bold warning stating exactly: "⚠ COULD NOT VERIFY THIS PART OF THE ASSESSMENT — treat as requiring human review." and set both risk levels to RED.

**STEP 1 — Build the report with these sections (in this order):**

1. **Executive Summary** (2-4 sentences):
   A plain-English overview of the key findings across both frameworks.
   State whether the system is likely low-risk, medium-risk, or high-risk overall.

2. **GDPR Readiness** subsection:
   - **GDPR Risk Level:** output EXACTLY one of these three strings (copy character-for-character):
       - 🔴 **RED** — if any checkpoint with risk_if_missing="high" is unaddressed or unclear
       - 🟡 **YELLOW** — if only medium-risk checkpoints are unaddressed or unclear
       - 🟢 **GREEN** — if all checkpoints are addressed
   - Format ALL checkpoints evaluated by the GDPR Agent as a Markdown TABLE with the following columns: Checkpoint Name, Status (e.g., ✅ Addressed, ❌ Unaddressed, ⚠️ Unclear, 🔶 Partial), Risk Level, and Rationale.
   - For any FLAGGED checkpoint (status = "unaddressed", "unclear", or "partial"), populate the Rationale column with the rationale and guidance_if_flagged. For unflagged checkpoints, provide a brief rationale.
   - Do NOT output any summary sentences or paragraphs below the GDPR results table.

3. **EU AI Act Classification** subsection:
   - **EU AI Act Risk Level:** output EXACTLY one of these three strings (copy character-for-character):
       - 🔴 **RED** — if classification is unacceptable_risk or high_risk
       - 🟡 **YELLOW** — if classification is limited_risk
       - 🟢 **GREEN** — if classification is minimal_risk
   - State the classification tier, matched category, assumed role, and obligations
   - If `fria_required` is true, YOU MUST INCLUDE this distinct labeled line: "⚠ FUNDAMENTAL RIGHTS IMPACT ASSESSMENT REQUIRED (Article 27) — must be completed before first use"
   - State whether obligations are currently in force or upcoming (from status_note)
   - State whether escalate_to_human is true or false

4. **Consolidated Action Items**:
   A numbered list of the specific things the organization should do before deployment,
   drawn from both the GDPR guidance_if_flagged items and the EU AI Act obligations.
   For each action item, include a tentative planned completion date formatted EXACTLY as a nested bullet point: "  - Planned Completion: [X] days" (where X is e.g. 15, 30, or 60). Do NOT use any other phrasing.

5. **Disclaimer** (MANDATORY — you MUST always include this as the final section,
   regardless of risk level, every single time, no exceptions):

"---
**Disclaimer:** This report is an automated first-pass readiness check produced by an AI system.
It is NOT legal advice, a compliance certification, or a substitute for professional legal review.
A qualified compliance professional should review these findings before any real deployment or
business decision is made."

**Output rules:**
- Use clear markdown formatting with headers and bullet points.
- Be specific — reference checkpoint IDs, article numbers, and category names.
- Do NOT invent findings that are not in the upstream agent outputs.
- Do NOT omit the escalation warning if the conditions are met.
- Do NOT omit the disclaimer under any circumstances.
"""

# ---------------------------------------------------------------------------
# Create the LlmAgent
# ---------------------------------------------------------------------------
# The aggregator has no tools — it works purely from the upstream outputs
# injected into its instruction via state variables.
#
# output_key="final_report" saves its response to session state so the
# run_compliance_check() helper can retrieve it.
aggregator_agent = LlmAgent(
    name="aggregator_agent",
    model=LiteLlm(model="openai/gpt-4o-mini"),
    instruction=AGGREGATOR_INSTRUCTION,
    description=(
        "Combines GDPR and EU AI Act evaluation outputs into a unified "
        "compliance readiness report with escalation gate and legal disclaimer."
    ),
    output_key="final_report",
)
