import asyncio
import io
import sys
from dotenv import load_dotenv
load_dotenv()
from agent import run_compliance_check
from app import EXAMPLES

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def main():
    names = [
        "Resume Screener",
        "Customer Support Chatbot",
        "Credit Scoring Tool",
        "Marketing Image Generator",
        "Meeting Notes Summariser"
    ]
    for i, item in enumerate(EXAMPLES):
        desc = item[0]
        name = names[i]
        print(f"\n=========================================")
        print(f"Scenario: {name}")
        print(f"=========================================")
        report = await run_compliance_check(desc)
        lines = report.split('\n')
        gdpr_risk = [l for l in lines if 'GDPR Risk Level:' in l]
        ai_risk = [l for l in lines if 'EU AI Act Risk Level:' in l]
        print(f"GDPR Risk: {gdpr_risk[0] if gdpr_risk else 'Not found'}")
        print(f"EU AI Act Risk: {ai_risk[0] if ai_risk else 'Not found'}")
        
        # Check if escalate_to_human is listed
        escalate = [l for l in lines if 'Escalate to Human:' in l]
        if escalate:
            print(f"Escalate: {escalate[0]}")
            
        summary_lines = [l for l in lines if 'Overall Summary' in l]
        if summary_lines:
            idx = lines.index(summary_lines[0])
            print(lines[idx])
            if idx + 1 < len(lines):
                print(lines[idx + 1])
        print("-----------------------------------------")

asyncio.run(main())
