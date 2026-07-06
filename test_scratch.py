import asyncio
import json
from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.intake_agent import intake_agent
from agents.eu_ai_act_agent import eu_ai_act_agent
from agent import run_compliance_check

async def test_eu_ai_act_standalone(desc):
    session_service = InMemorySessionService()
    intake_runner = Runner(agent=intake_agent, app_name='test', session_service=session_service)
    session = await session_service.create_session(app_name='test', user_id='u1')
    
    intake_result = ''
    async for event in intake_runner.run_async(user_id='u1', session_id=session.id, new_message=types.Content(role='user', parts=[types.Part.from_text(text=desc)])):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    intake_result = part.text

    eu_runner = Runner(agent=eu_ai_act_agent, app_name='test2', session_service=session_service)
    session2 = await session_service.create_session(app_name='test2', user_id='u2')
    session2.state['intake_result'] = intake_result
    
    print(f'\n--- EU AI ACT STANDALONE TEST ---')
    print(f'INPUT: {desc}')
    
    eu_result = ''
    async for event in eu_runner.run_async(user_id='u2', session_id=session2.id, new_message=types.Content(role='user', parts=[types.Part.from_text(text='evaluate the AI system based on the provided intake result.')])):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    eu_result = part.text
    print(eu_result)

async def test_full_pipeline(desc):
    print(f'\n--- FULL PIPELINE TEST ---')
    print(f'INPUT: {desc}')
    res = await run_compliance_check(desc)
    print(res)

async def main():
    await test_eu_ai_act_standalone('An AI credit-scoring tool for a bank determining loan eligibility')
    await test_eu_ai_act_standalone('An AI tool that screens job applicant resumes and ranks candidates')
    await test_eu_ai_act_standalone('AI software embedded in a medical device that assists doctors in diagnosing patient conditions')
    
    await test_full_pipeline('An AI tool that screens job applicant resumes and ranks candidates')
    await test_full_pipeline('An AI credit-scoring tool for a bank determining loan eligibility')
    await test_full_pipeline('An e-commerce chatbot')
    await test_full_pipeline('An internal meeting summarizer')
    await test_full_pipeline('A marketing image generator')
    await test_full_pipeline('AI software embedded in a medical device that assists doctors in diagnosing patient conditions')

if __name__ == '__main__':
    asyncio.run(main())
