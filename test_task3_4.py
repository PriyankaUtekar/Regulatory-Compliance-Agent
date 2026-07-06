import asyncio
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.agents import SequentialAgent

from agents.intake_agent import INTAKE_INSTRUCTION
from agents.eu_ai_act_agent import EU_AI_ACT_INSTRUCTION, load_eu_ai_act_risk_tree, regulatory_mcp_toolset
from google.adk.agents import LlmAgent
from google.adk.models import LiteLlm
from agent import run_compliance_check

async def test_task3():
    print("=" * 90)
    print("TASK 3: STANDALONE EU AI ACT TEST")
    print("=" * 90)
    
    test_intake = LlmAgent(name="intake", model=LiteLlm(model="openai/gpt-4o-mini"), instruction=INTAKE_INSTRUCTION, output_key="intake_result")
    test_eu = LlmAgent(name="eu_ai_act_agent", model=LiteLlm(model="openai/gpt-4o-mini"), instruction=EU_AI_ACT_INSTRUCTION, tools=[load_eu_ai_act_risk_tree, regulatory_mcp_toolset])
    
    agent = SequentialAgent(
        name="test_pipeline",
        description="test",
        sub_agents=[test_intake, test_eu]
    )

    
    scenarios = [
        "An AI credit-scoring tool for a bank determining loan eligibility",
        "An AI tool that screens job applicant resumes and ranks candidates",
        "AI software embedded in a medical device that assists doctors in diagnosing patient conditions"
    ]
    
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="test", session_service=session_service)
    
    for i, sc in enumerate(scenarios):
        print(f"\n[Scenario {i+1}] {sc}")
        session = await session_service.create_session(app_name="test", user_id="api_user")
        user_content = types.Content(role="user", parts=[types.Part.from_text(text=sc)])
        
        output = ""
        async for event in runner.run_async(user_id="api_user", session_id=session.id, new_message=user_content):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and event.author == "eu_ai_act_agent":
                        output = part.text
        
        print(output)
        await asyncio.sleep(5)

async def test_task4():
    print("\n\n" + "=" * 90)
    print("TASK 4: FULL PIPELINE TEST")
    print("=" * 90)
    
    scenarios = [
        "An AI tool that screens job applicant resumes and ranks candidates",
        "An AI credit-scoring tool for a bank determining loan eligibility",
        "A customer support chatbot for an e-commerce site, no sensitive data logged",
        "An internal tool that summarizes employee meeting notes, no HR decisions made",
        "An AI tool generating marketing images for social media posts",
        "AI software embedded in a medical device that assists doctors in diagnosing patient conditions"
    ]
    
    for i, sc in enumerate(scenarios):
        print(f"\n{'-' * 90}")
        print(f"Scenario {i+1}: {sc}")
        print(f"{'-' * 90}\n")
        
        start_time = time.time()
        try:
            report = await run_compliance_check(sc)
            print(report)
        except Exception as e:
            print(f"ERROR: {e}")
        
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(test_task3())
    asyncio.run(test_task4())
