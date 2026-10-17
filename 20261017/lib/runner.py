"""エージェントに1問答えさせる（触らない）。"""

import asyncio
import importlib
import logging
import os
import warnings

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# 学生の画面に出ても意味のない、ADKの実験機能の警告とログを止める
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\]")
# エラーは lib/cli.py で短く出すので、ADKが出す長いトレースバックも止める（HANDSON_DEBUG=1 なら出す）
if os.getenv("HANDSON_DEBUG") != "1":
    logging.getLogger("google_adk").setLevel(logging.CRITICAL)

APP = "handson"
USER = "student"


def load_agent(module: str = "my_agent.agent"):
    return importlib.import_module(module).root_agent


async def _ask(agent, question: str) -> dict:
    sessions = InMemorySessionService()
    runner = Runner(agent=agent, app_name=APP, session_service=sessions)
    session = await sessions.create_session(app_name=APP, user_id=USER)
    message = types.Content(role="user", parts=[types.Part(text=question)])

    answer, tool_calls = "", []
    async for event in runner.run_async(user_id=USER, session_id=session.id, new_message=message):
        for call in event.get_function_calls():
            tool_calls.append({"name": call.name, "args": dict(call.args or {}), "response": None})
        for res in event.get_function_responses():
            for call in tool_calls:
                if call["name"] == res.name and call["response"] is None:
                    call["response"] = res.response
                    break
        if event.is_final_response() and event.content and event.content.parts:
            answer = "".join(p.text or "" for p in event.content.parts)
    return {"question": question, "answer": answer, "tool_calls": tool_calls}


def ask(agent, question: str) -> dict:
    """回答と、途中で呼ばれたツールの一覧（引数と結果）を返す。"""
    return asyncio.run(_ask(agent, question))
