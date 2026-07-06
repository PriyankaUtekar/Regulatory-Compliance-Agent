"""
Full Pipeline Test — 5 Compliance Scenarios
=============================================
Runs the complete pipeline (Intake → GDPR + EU AI Act in parallel → Aggregator)
against 5 test scenarios to validate escalation gate behavior.

Usage:
    cd d:\\compliance_agent
    .venv\\Scripts\\python.exe test_agents.py

Expected results:
  (a) Resume screener    → HIGH-RISK, escalation triggered
  (b) Credit scoring     → HIGH-RISK, escalation triggered
  (c) Support chatbot    → LIMITED-RISK, no escalation
  (d) Meeting summarizer → MINIMAL/edge case, may flag for review
  (e) Marketing images   → LIMITED-RISK, no escalation
"""

import asyncio
import sys
import io
import time

# Fix Windows console encoding to handle unicode characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load environment variables (GOOGLE_API_KEY) from .env file
from dotenv import load_dotenv
load_dotenv()

# Import the convenience function from the root orchestrator
from agent import run_compliance_check

# ---------------------------------------------------------------------------
# The 5 test scenarios
# ---------------------------------------------------------------------------
SCENARIOS = [
    {
        "label": "SCENARIO A — Resume Screener (expect HIGH-RISK escalation)",
        "input": (
            "An AI tool that screens job applicant resumes and ranks candidates"
        ),
        "expect_escalation": True,
    },
    {
        "label": "SCENARIO B — Credit Scoring (expect HIGH-RISK escalation)",
        "input": (
            "An AI credit-scoring tool for a bank determining loan eligibility"
        ),
        "expect_escalation": True,
    },
    {
        "label": "SCENARIO C — Customer Support Chatbot (expect LIMITED-RISK, no escalation)",
        "input": (
            "A customer support chatbot for an e-commerce site, no sensitive data logged"
        ),
        "expect_escalation": False,
    },
    {
        "label": "SCENARIO D — Meeting Notes Summarizer (expect MINIMAL-RISK edge case)",
        "input": (
            "An internal tool that summarizes employee meeting notes, no HR decisions made"
        ),
        "expect_escalation": False,  # Might flag for manual review but shouldn't hard-escalate
    },
    {
        "label": "SCENARIO E — Marketing Image Generator (expect LIMITED-RISK, no escalation)",
        "input": (
            "An AI tool generating marketing images for social media posts"
        ),
        "expect_escalation": False,
    },
]

# The exact escalation warning text the aggregator must include
ESCALATION_MARKER = (
    "HUMAN REVIEW REQUIRED"
)


async def run_all_scenarios():
    """Run all 5 test scenarios and print results with pass/fail validation."""

    print("=" * 90)
    print("COMPLIANCE PIPELINE — Full Integration Test (5 Scenarios)")
    print("=" * 90)

    results = []

    for i, scenario in enumerate(SCENARIOS):
        print(f"\n{'-' * 90}")
        print(f"  {scenario['label']}")
        print(f"  Input: \"{scenario['input']}\"")
        print(f"{'-' * 90}\n")

        start_time = time.time()

        try:
            report = await run_compliance_check(scenario["input"])
            elapsed = time.time() - start_time

            # Print the full report
            print(report)
            print(f"\n⏱  Completed in {elapsed:.1f}s")

            # Validate escalation gate
            has_escalation = ESCALATION_MARKER in report
            expected = scenario["expect_escalation"]

            if has_escalation == expected:
                status = "✅ PASS"
                detail = (
                    "Escalation correctly triggered"
                    if expected
                    else "Escalation correctly NOT triggered"
                )
            else:
                status = "❌ FAIL"
                detail = (
                    f"Expected escalation={'YES' if expected else 'NO'}, "
                    f"got escalation={'YES' if has_escalation else 'NO'}"
                )

            print(f"\n{status}: {detail}")
            results.append((scenario["label"], status, detail))

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ ERROR after {elapsed:.1f}s: {e}")
            results.append((scenario["label"], "❌ ERROR", str(e)))

        # Brief pause between scenarios to respect rate limits
        if i < len(SCENARIOS) - 1:
            print("\n⏳ Pausing 5s before next scenario (rate limit buffer)...")
            await asyncio.sleep(5)

    # ---------------------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------------------
    print(f"\n\n{'=' * 90}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 90}")
    for label, status, detail in results:
        print(f"  {status}  {label}")
        print(f"         {detail}")
    print(f"{'=' * 90}")

    # Count passes
    passes = sum(1 for _, s, _ in results if "PASS" in s)
    total = len(results)
    print(f"\n  {passes}/{total} scenarios passed.\n")


if __name__ == "__main__":
    asyncio.run(run_all_scenarios())
