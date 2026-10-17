"""あなたのエージェント。このファイルを作り変える。

いまは「こんにちは」に返事をするだけで、QAは見ていない。
  python ask.py "こんにちは"
"""

from datetime import datetime

from google.adk.agents import Agent

from lib.model import get_model
from lib.rag import RagError, load_qa, qa_files, search


def search_qa(query: str, k: int = 3) -> list[dict]:
    """42 Tokyoについての質問と答え（QA）を検索する。

    42 Tokyoについて答える前に、必ずこのツールで関連するQAを調べ、
    見つかった答えをもとに回答する。

    Args:
        query: 検索したい質問文。
        k: 取得する件数（省略時は3件）。

    Returns:
        question, answer, source, score を持つ辞書のリスト。
    """
    return search(query, k)


def search_my_qa(query: str, k: int = 3) -> list[dict] | dict:
    """自分（my_qa.csv）が書いたQAだけを検索する。

    「42 Tokyoの大変なところは何ですか？」のように、公式サイトに載っていない
    本人の意見や感想を聞かれたときに使う。secret_qa.csv など他のQAは対象にしない。

    Args:
        query: 検索したい質問文。
        k: 取得する件数（省略時は3件）。

    Returns:
        question, answer, source, score を持つ辞書のリスト（source は my_qa.csv のみ）。
        見つからない、または検索できないときは error を持つ辞書。
    """
    try:
        results = [r for r in search(query, k=20) if r["source"] == "my_qa.csv"][:k]
        if not results:
            return {"error": "my_qa.csv に、それに近いQAが見つかりませんでした。"}
        return results
    except RagError as e:
        return {"error": str(e)}


def list_answerable_questions() -> dict:
    """登録されている、答えられる質問の一覧を返す。

    「どんなことに答えられますか？」のような質問で使う。

    Returns:
        questions（質問文のリスト）を持つ辞書。読み込めないときは error を持つ辞書。
    """
    try:
        rows = load_qa(qa_files())
        if not rows:
            return {"error": "登録されているQAがありません。"}
        return {"questions": [r["question"] for r in rows]}
    except OSError as e:
        return {"error": str(e)}


def calculate_study_hours(hours_per_week: float, months: float) -> dict:
    """週あたりの学習時間と続ける月数から、合計の学習時間を計算する。

    「週35時間を半年続けると、全部で何時間ですか？」のような質問で使う。

    Args:
        hours_per_week: 1週間あたりの学習時間。
        months: 続ける期間（月数）。

    Returns:
        total_hours（合計時間）を持つ辞書。計算できないときは error を持つ辞書。
    """
    try:
        if hours_per_week < 0 or months < 0:
            raise ValueError("hours_per_week と months は0以上で指定してください。")
        total_hours = hours_per_week * months * 4
        return {"hours_per_week": hours_per_week, "months": months, "total_hours": round(total_hours, 1)}
    except (TypeError, ValueError) as e:
        return {"error": str(e)}


def get_today() -> dict:
    """今日の日付と曜日を返す。「今日は何曜日ですか？」のような質問で使う。

    Returns:
        date（YYYY-MM-DD）と weekday（曜日）を持つ辞書。失敗したときは error を持つ辞書。
    """
    try:
        now = datetime.now()
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        return {"date": now.strftime("%Y-%m-%d"), "weekday": f"{weekdays[now.weekday()]}曜日"}
    except Exception as e:
        return {"error": str(e)}


INSTRUCTION = "あなたは42 Tokyoについて答えるアシスタントです。日本語で答えてください。"


root_agent = Agent(
    name="my_agent",
    model=get_model(),
    instruction=INSTRUCTION,
    tools=[search_qa, search_my_qa, list_answerable_questions, calculate_study_hours, get_today],
)
