"""
Intake Agent
=============
Takes a free-text description of an AI system that a business wants to deploy
and extracts structured fields so downstream compliance agents can evaluate it.

Extracted fields:
  - purpose:             What the AI system does
  - data_types_processed: What personal/other data it handles
  - decision_type:       Does it make or influence decisions about people?
  - affected_users:      Who is affected (employees, customers, public, etc.)
  - geography:           Where it operates / whose data it processes

This agent has NO tools — it relies entirely on the LLM's comprehension to
parse the free-text input into a structured JSON output.
"""

from google.adk.agents import LlmAgent
from google.adk.models import LiteLlm

# ---------------------------------------------------------------------------
# System instruction for the Intake Agent
# ---------------------------------------------------------------------------
# The instruction tells the LLM exactly what to extract and how to format it.
# We ask for JSON so downstream agents can parse it programmatically.
INTAKE_INSTRUCTION = """You are the **Intake Agent** for a regulatory compliance-checking system.

Your ONLY job is to read the user's plain-text description of an AI system and
extract the following structured fields. Do NOT evaluate compliance — just extract facts.

**Fields to extract (return as valid JSON):**

1. `purpose` (string): A one-to-two-sentence summary of what the AI system does.
2. `data_types_processed` (list of strings): Every category of personal or
   sensitive data the system appears to process (e.g. "names", "CVs/resumes",
   "LinkedIn profile data", "employment history", "biometric data").
3. `decision_type` (string): One of:
   - "automated_decision" — the system makes decisions about people with no human in the loop
   - "decision_support" — the system assists or recommends but a human decides
   - "no_personal_decision" — the system does not make or influence decisions about people
   - "unclear" — not enough information to determine
4. `affected_users` (list of strings): Who is affected by the system
   (e.g. "job applicants", "employees", "customers", "general public").
5. `geography` (string): Where the system operates or whose data it processes.
   If not explicitly stated, output "not_specified".
6. `project_release_date` (string): The planned release or deployment date of the project (e.g. "August 15, 2026").
   If not explicitly stated, output "not_specified".

**Output rules:**
- Return ONLY a single JSON object with these six keys — no markdown fences,
  no explanatory text before or after.
- If information is missing or ambiguous for a field, make your best inference
  and add a parenthetical "(inferred)" note in the value.
- Be factual. Do not add information the user did not mention or imply.

**Important disclaimer:** This system provides a preliminary readiness/gap analysis
only. It is NOT a legal certification or legal advice.
"""

# ---------------------------------------------------------------------------
# Create the LlmAgent
# ---------------------------------------------------------------------------
# In ADK v2.x, LlmAgent is constructed with keyword arguments.
# - name:        unique identifier for the agent (used in logs & the web UI)
# - model:       the Gemini model to use (gemini-2.0-flash is fast & capable)
# - instruction: the system prompt that tells the LLM how to behave
#
# We intentionally do NOT set tools=[] because this agent needs no tools —
# it only uses the LLM's built-in language understanding.
intake_agent = LlmAgent(
    name="intake_agent",
    model=LiteLlm(model="openai/gpt-4o-mini"),
    instruction=INTAKE_INSTRUCTION,
    description=(
        "Parses a free-text description of an AI system into structured fields "
        "(purpose, data types, decision type, affected users, geography) "
        "for downstream compliance evaluation."
    ),
    # output_key saves this agent's final response into session state under
    # the key "intake_result". Downstream agents (GDPR, EU AI Act) can then
    # reference it as {intake_result} in their instruction templates.
    output_key="intake_result",
)
