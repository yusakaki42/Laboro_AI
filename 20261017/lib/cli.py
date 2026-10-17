"""コマンドの共通処理（触らない）。"""

import json
import os
import sys

from lib.rag import RagError, api_key_name, is_mock


def fail(message: str, code: int = 1):
    print(f"[エラー] {message}", file=sys.stderr)
    sys.exit(code)


def check_keys():
    """APIキーがなければ、何をすればよいかを伝えて止める。"""
    if not is_mock() and not os.getenv(api_key_name()):
        fail(f".env に {api_key_name()} がありません。当日配られたキーを .env に書いてください。"
             "キーなしで試すときは .env の HANDSON_MOCK=1 にします。", code=2)


def run(main):
    """main() を実行し、エラーは短いメッセージにして止める。HANDSON_DEBUG=1 なら詳細をそのまま出す。"""
    check_keys()
    try:
        main()
    except RagError as e:
        fail(str(e))
    except Exception as e:
        if os.getenv("HANDSON_DEBUG") == "1":
            raise
        first = (str(e).strip().splitlines() or [""])[0]
        fail(f"{type(e).__name__}: {first}\n詳しく見るときは HANDSON_DEBUG=1 を付けて実行する。")


def print_hits(hits: list[dict], answers: bool = False):
    """検索結果を「点数・ファイル・質問」の表にして出す。answers=True なら、答えの書き出しも出す。"""
    for rank, h in enumerate(hits, 1):
        print(f"  {rank}. {h['score']:.3f}  {h['source']:<16}  {h['question']}")
        if answers and h.get("answer"):
            answer = str(h["answer"]).replace("\n", " ")
            print(f"     答え: {answer[:60]}{'…' if len(answer) > 60 else ''}")


def find_hits(value) -> list[dict]:
    """ツールの結果の中から、検索で引けたQA（score と source を持つもの）を探す。"""
    if isinstance(value, dict):
        if "score" in value and "source" in value:
            return [value]
        return [h for v in value.values() for h in find_hits(v)]
    if isinstance(value, list):
        return [h for v in value for h in find_hits(v)]
    return []


def show_response(response, limit: int = 400, answers: bool = False):
    """ツールの戻り値をそのまま出し、引けたQAがあれば点数とファイル名の表も出す。"""
    text = json.dumps(response, ensure_ascii=False, default=str)
    print(f"  [戻り値] {text[:limit]}{' …（以下略）' if len(text) > limit else ''}")
    hits = find_hits(response)
    if hits:
        print_hits(hits, answers=answers)
    else:
        print("  （点数とファイル名を持つQAが見つかりません。search の結果を文字列にせず、そのまま返すと表示されます）")
