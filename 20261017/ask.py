"""エージェントに1問答えさせる（S6、S7、S8）。

「[1] 調べる → [2] 引けた資料 → [3] 回答」の3段で表示する。エージェントが何を調べ、
どの資料をもとに答えたかを、上から順にたどれる。

  python ask.py "質問"
  python ask.py --save "質問"      回答を out/answers.jsonl に残す（S7、S8）
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from lib.cli import run, show_response
from lib.runner import ask, load_agent

ANSWERS = Path(__file__).resolve().parent / "out" / "answers.jsonl"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question")
    parser.add_argument("--save", action="store_true", help="回答を out/answers.jsonl に追記する")
    parser.add_argument("--agent", default="my_agent.agent", help="root_agent を持つモジュール")
    args = parser.parse_args()

    result = ask(load_agent(args.agent), args.question)
    calls = result["tool_calls"]

    print("[1] 調べる: エージェントが呼んだツール")
    if not calls:
        print("  呼ばれていません（LLMが、もともと知っていることだけで答えました）")
    for call in calls:
        print(f"  {call['name']}({json.dumps(call['args'], ensure_ascii=False)})")

    if calls:
        print("\n[2] 引けた資料: ツールが返したもの")
        for call in calls:
            if len(calls) > 1:
                print(f"  ({call['name']} の結果)")
            show_response(call["response"], answers=True)

    print("\n[3] 回答: 引けた資料をもとに、LLMが書いた答え" if calls else "\n[3] 回答")
    print(result["answer"])

    if args.save:
        ANSWERS.parent.mkdir(parents=True, exist_ok=True)
        record = {"time": datetime.now().isoformat(timespec="seconds"), "agent": args.agent, **result}
        with ANSWERS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        print(f"\n[保存] {ANSWERS.relative_to(ANSWERS.parent.parent)} に追記しました")


if __name__ == "__main__":
    run(main)
