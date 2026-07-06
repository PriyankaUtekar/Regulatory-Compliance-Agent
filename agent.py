"""
Root Orchestrator — agent.py
==============================
This is the entry point for both `adk web` and the `run_compliance_check()`
helper function. It wires the full compliance pipeline:

    User's free-text description
            │
            ▼
    ┌───────────────┐
    │ Intake Agent   │  ← extracts structured fields (output_key="intake_result")
    └───────┬───────┘
            │
    ┌───────┴───────┐
    │  ParallelAgent │  ← runs GDPR + EU AI Act simultaneously
    │  ┌───────────┐ │
    │  │ GDPR Agent│ │  ← evaluates checkpoints (output_key="gdpr_result")
    │  └───────────┘ │
    │  ┌───────────┐ │
    │  │EU AI Agent│ │  ← classifies risk tier (output_key="eu_ai_act_result")
    │  └───────────┘ │
    └───────┬───────┘
            │
    ┌───────┴────────┐
    │ Aggregator Agent│  ← merges both into final report (output_key="final_report")
    └────────────────┘

Composition:
  - SequentialAgent runs the three stages in order.
  - ParallelAgent (nested inside the sequential) runs GDPR and EU AI Act
    concurrently since they only depend on intake_result, not on each other.

Data flow uses ADK's output_key → {state_variable} mechanism:
  1. intake_agent saves to state["intake_result"]
  2. gdpr_agent reads {intake_result}, saves to state["gdpr_result"]
  3. eu_ai_act_agent reads {intake_result}, saves to state["eu_ai_act_result"]
  4. aggregator_agent reads {gdpr_result} and {eu_ai_act_result}
"""

from google.adk.agents import SequentialAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event

# Import the four sub-agents
from agents.intake_agent import intake_agent
from agents.gdpr_agent import gdpr_agent
from agents.eu_ai_act_agent import eu_ai_act_agent
from agents.aggregator_agent import aggregator_agent

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

def log_audit_failure(agent_name: str, input_data: str, error_reason: str):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "audit_log.jsonl"
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent_name,
        "input": input_data,
        "failure_reason": error_reason
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def log_audit_success(agent_name: str, message: str):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "audit_log.jsonl"
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent_name,
        "success_message": message
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def validate_gdpr(response_text: str) -> tuple[bool, str]:
    try:
        if response_text.startswith("```"):
            response_text = "\n".join(response_text.split("\n")[1:-1])
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
        
    if "checkpoints" not in data or "overall" not in data:
        return False, "Missing 'checkpoints' or 'overall' key."
        
    knowledge_path = Path(__file__).resolve().parent / "knowledge" / "gdpr_checklist.json"
    with open(knowledge_path, "r", encoding="utf-8") as f:
        checklist = json.load(f)
        
    expected_ids = {cp["id"] for cp in checklist["checklist"]}
    actual_ids = {cp.get("checkpoint_id") or cp.get("id") for cp in data["checkpoints"]}
    
    missing_ids = expected_ids - actual_ids
    if missing_ids:
        return False, f"Missing evaluations for checkpoint IDs: {missing_ids}"
        
    return True, ""

def validate_eu_ai_act(response_text: str) -> tuple[bool, str]:
    try:
        if response_text.startswith("```"):
            response_text = "\n".join(response_text.split("\n")[1:-1])
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
        
    required_keys = {"classification", "matched_category_or_trigger", "assumed_role", "obligations", "fria_required", "status_note", "escalate_to_human"}
    missing_keys = required_keys - set(data.keys())
    if missing_keys:
        return False, f"Missing required fields: {missing_keys}"
        
    valid_tiers = {"unacceptable_risk", "high_risk", "limited_risk", "minimal_risk"}
    if data["classification"] not in valid_tiers:
        return False, f"Invalid classification '{data['classification']}'. Must be one of {valid_tiers}."
        
    if data["classification"] != "minimal_risk":
        knowledge_path = Path(__file__).resolve().parent / "knowledge" / "eu_ai_act_risk_tree.json"
        with open(knowledge_path, "r", encoding="utf-8") as f:
            risk_tree = json.load(f)
        
        valid_ids = set()
        for p in risk_tree["risk_tiers"]["unacceptable_risk"]["prohibited_practices"]:
            valid_ids.add(p["id"])
        for c in risk_tree["risk_tiers"]["high_risk"]["classification_routes"]["route_1_annex_iii_use_case"]["categories"]:
            valid_ids.add(c["id"])
        for c in risk_tree["risk_tiers"]["high_risk"]["classification_routes"]["route_2_annex_i_regulated_product"]["categories"]:
            valid_ids.add(c["id"])
        for t in risk_tree["risk_tiers"]["limited_risk"]["transparency_triggers"]:
            valid_ids.add(t["id"])
            
        matched_category = data["matched_category_or_trigger"]
        if not any(vid in matched_category for vid in valid_ids):
            return False, f"matched_category_or_trigger '{matched_category}' does not correspond to an id that actually exists in knowledge/eu_ai_act_risk_tree.json"
            
    return True, ""

async def call_agent_with_remediation(agent: BaseAgent, input_data: str, validate_fn, ctx: InvocationContext, max_retries=1) -> AsyncGenerator[Event, None]:
    retry_count = 0
    current_agent = agent
    
    while retry_count <= max_retries:
        ctx.set_agent_state(current_agent.name) # clear state
        response_text = ""
        events = []
        async for event in current_agent.run_async(ctx):
            events.append(event)
            if event.content and event.content.parts and event.author == current_agent.name:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
        for event in events:
            yield event
            
        is_valid, error_msg = validate_fn(response_text)
        if is_valid:
            if retry_count > 0:
                log_audit_success(current_agent.name, "Remediation succeeded on retry.")
            return
            
        log_audit_failure(current_agent.name, input_data, error_msg)
        
        retry_count += 1
        if retry_count <= max_retries:
            new_instruction = current_agent.instruction + f"\n\nYour previous response was invalid because: {error_msg}. Return ONLY a valid, complete response with all required fields as specified in your instructions."
            current_agent = current_agent.clone(update={"instruction": new_instruction})
            
    # Fail-closed signal
    fail_closed_msg = "⚠ COULD NOT VERIFY THIS PART OF THE ASSESSMENT — treat as requiring human review."
    fail_closed_json = {
        "error": fail_closed_msg,
        "escalate_to_human": True,
        "classification": "high_risk",
        "matched_category_or_trigger": "none",
        "assumed_role": "N/A",
        "obligations": [fail_closed_msg],
        "fria_required": False,
        "status_note": "failed",
        "checkpoints": [{"checkpoint_id": "failed", "checkpoint_name": "failed", "applicable": True, "status": "unaddressed", "risk_if_missing": "high", "rationale": fail_closed_msg}],
        "overall": {"high_risk_unaddressed_count": 1, "overall_color": "red", "summary": fail_closed_msg}
    }
    
    if hasattr(current_agent, "output_key") and current_agent.output_key:
         ctx.session.state[current_agent.output_key] = json.dumps(fail_closed_json)

# ---------------------------------------------------------------------------
# Stage 2: ParallelAgent — runs GDPR and EU AI Act concurrently
# ---------------------------------------------------------------------------
class ComplianceEvaluatorsAgent(BaseAgent):
    name: str = "compliance_evaluators"
    description: str = "Runs the GDPR and EU AI Act agents with validation and remediation."
    sub_agents: list[BaseAgent] = [gdpr_agent, eu_ai_act_agent]
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        intake_result = ctx.session.state.get("intake_result", "")
        
        queue = asyncio.Queue()
        
        async def run_agent(agent, validate_fn):
            try:
                async for event in call_agent_with_remediation(agent, intake_result, validate_fn, ctx):
                    await queue.put(event)
            finally:
                await queue.put(None)
                
        task1 = asyncio.create_task(run_agent(gdpr_agent, validate_gdpr))
        task2 = asyncio.create_task(run_agent(eu_ai_act_agent, validate_eu_ai_act))
        
        finished_tasks = 0
        while finished_tasks < 2:
            event = await queue.get()
            if event is None:
                finished_tasks += 1
            else:
                yield event
                
        await task1
        await task2

# ---------------------------------------------------------------------------
# Root agent: SequentialAgent — the full pipeline
# ---------------------------------------------------------------------------
# Stage 1: intake_agent   → extracts structured fields
# Stage 2: compliance_evaluators (parallel) → GDPR + EU AI Act
# Stage 3: aggregator_agent → merges results into final report
#
# `adk web` discovers this file and looks for `root_agent`.
root_agent = SequentialAgent(
    name="compliance_pipeline",
    description=(
        "Full compliance-checking pipeline: intake → parallel GDPR + EU AI Act "
        "evaluation → aggregated readiness report with escalation gate."
    ),
    sub_agents=[intake_agent, ComplianceEvaluatorsAgent(), aggregator_agent],
)


# ---------------------------------------------------------------------------
# Convenience function: run_compliance_check()
# ---------------------------------------------------------------------------
# This function provides a simple programmatic API for calling the full
# pipeline from a front-end, CLI, or test script. It creates a Runner,
# session, sends the user message, and returns the final report string.

async def run_compliance_check(description: str) -> str:
    """
    Run the full compliance pipeline on a free-text AI system description.

    Args:
        description: Plain-text description of the AI system to evaluate.
                     e.g. "An AI tool that screens job applicant resumes..."

    Returns:
        The final aggregated compliance readiness report as a string.

    Example:
        import asyncio
        from agent import run_compliance_check

        report = asyncio.run(run_compliance_check(
            "An AI tool that screens job applicant resumes and ranks candidates"
        ))
        print(report)
    """
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    # Create fresh session service and runner for this check
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="compliance_checker",
        session_service=session_service,
    )

    # Create a session
    session = await session_service.create_session(
        app_name="compliance_checker",
        user_id="api_user",
    )

    # Build the user message
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=description)],
    )

    # Run the pipeline and collect the final response
    # The aggregator_agent is the last agent in the sequence, so its output
    # is the final event with text content.
    final_report = ""
    async for event in runner.run_async(
        user_id="api_user",
        session_id=session.id,
        new_message=user_content,
    ):
        # Collect text from the aggregator_agent (the last agent to speak)
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and event.author == "aggregator_agent":
                    final_report = part.text

    return final_report
