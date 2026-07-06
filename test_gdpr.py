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
    test_input = "An AI tool that automatically screens job applicant resumes and ranks candidates for a hiring team, using data from LinkedIn profiles and submitted CVs."
    report = await run_compliance_check(test_input)
    print("Standalone Check:")
    print(report)

asyncio.run(main())
