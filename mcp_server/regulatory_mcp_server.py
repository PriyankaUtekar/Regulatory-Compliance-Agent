import json
from pathlib import Path
import urllib.request
import urllib.error
import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RegulatoryContext")

BASE_DIR = Path(__file__).resolve().parent.parent

@mcp.tool()
def get_gdpr_checklist() -> str:
    """Reads and returns the full contents of knowledge/gdpr_checklist.json."""
    knowledge_path = BASE_DIR / "knowledge" / "gdpr_checklist.json"
    try:
        with open(knowledge_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading GDPR checklist: {e}"

@mcp.tool()
def get_eu_ai_act_risk_tree() -> str:
    """Reads and returns the full contents of knowledge/eu_ai_act_risk_tree.json."""
    knowledge_path = BASE_DIR / "knowledge" / "eu_ai_act_risk_tree.json"
    try:
        with open(knowledge_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading EU AI Act risk tree: {e}"

@mcp.tool()
def check_eu_ai_act_timeline_status() -> str:
    """Fetches the current EU AI Act implementation timeline status from a public web page."""
    fallback_string = (
        "LIVE CHECK UNAVAILABLE — using last known status: prohibited practices "
        "in force since Feb 2025; GPAI obligations in force since Aug 2025; "
        "Annex III high-risk obligations deferred to Dec 2027 per May 2026 "
        "political agreement; Article 50 transparency obligations apply from Aug 2026. "
        "(Confirm current status manually before relying on this for a real compliance decision.)"
    )
    import requests
    url = "https://artificialintelligenceact.eu/"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2.0)
        response.raise_for_status()
        html = response.text
        # Extract a brief summary (first few chars) just to prove the live fetch worked.
        # In a real app we would parse specific HTML elements.
        summary = html[:200].replace('\n', ' ')
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"LIVE CHECK SUCCESSFUL ({timestamp}) — Found page content. (Snippet: {summary})"
    except Exception:
        return fallback_string

if __name__ == "__main__":
    mcp.run(transport='stdio')
