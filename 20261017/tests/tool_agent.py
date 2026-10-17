"""try_tool.py の試験用のエージェント。検索の代わりに、決まった結果を返すツールを持つ。"""

from google.adk.agents import Agent

from lib.model import get_model


def fake_search(query: str, k: int = 1) -> dict:
    """試験用。質問をそのまま、点数つきのQAとして k 件返す。"""
    return {"results": [{"question": query, "answer": "試験", "source": "test.csv", "score": 0.5}] * k}


def plain_text(query: str) -> str:
    """試験用。文字列を返す。"""
    return f"結果: {query}"


root_agent = Agent(name="tool_agent", model=get_model(), tools=[fake_search, plain_text])
