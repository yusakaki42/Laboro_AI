"""ツール関数を、LLMを通さずに直接呼んで確かめる（S6）。

  python try_tool.py                      つないだツールの一覧と、LLMに見えている説明を出す
  python try_tool.py ツール名 引数...      そのツールを直接呼び、戻り値を出す
  例: python try_tool.py search_qa "今日のハンズオンの合言葉は？"
"""

import argparse
import asyncio
import inspect
import warnings

from google.adk.tools import FunctionTool

from lib.cli import fail, run, show_response
from lib.runner import load_agent

CONVERT = {int: int, float: float, bool: lambda s: s.lower() in ("1", "true", "yes")}


def tool_functions(agent) -> dict:
    """エージェントにつないだツールを、名前と関数の組にして返す。"""
    funcs = {}
    for tool in agent.tools:
        func = getattr(tool, "func", tool)
        if callable(func) and hasattr(func, "__name__"):
            funcs[func.__name__] = func
    return funcs


def describe(func):
    """LLMに見えている、ツールの名前・説明・引数を出す。"""
    with warnings.catch_warnings():
        # ADK の「EXPERIMENTAL」の警告は、学生の画面では読まなくてよいので出さない
        warnings.simplefilter("ignore", UserWarning)
        decl = FunctionTool(func)._get_declaration()
    print(f"[ツール] {decl.name}")
    print(f"  説明: {decl.description or '（docstring がありません。LLMは、いつ使えばよいかが分かりません）'}")
    props = (decl.parameters.properties or {}) if decl.parameters else {}
    if not props:
        schema = getattr(decl, "parameters_json_schema", None) or {}
        props = schema.get("properties", {})
    if not props:
        print("  引数: なし")
    for name, prop in props.items():
        kind = prop.get("type") if isinstance(prop, dict) else getattr(prop, "type", None)
        desc = prop.get("description") if isinstance(prop, dict) else getattr(prop, "description", None)
        kind = getattr(kind, "value", kind)
        print(f"  引数: {name}（{str(kind).lower() if kind else '型なし'}）{'  ' + desc if desc else ''}")


def call(func, raw_args: list[str]):
    """文字列で受け取った引数を型に合わせて変換し、関数を呼ぶ。"""
    params = [p for p in inspect.signature(func).parameters.values() if p.name != "tool_context"]
    if len(raw_args) > len(params):
        fail(f"引数が多すぎます。{func.__name__} の引数は {[p.name for p in params]} です。")
    args = [CONVERT.get(p.annotation, str)(a) for p, a in zip(params, raw_args)]
    result = func(*args)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tool", nargs="?", help="呼ぶツールの名前。省略すると一覧を出す")
    parser.add_argument("args", nargs="*", help="ツールに渡す引数（順番どおり）")
    parser.add_argument("--agent", default="my_agent.agent", help="root_agent を持つモジュール")
    args = parser.parse_args()

    funcs = tool_functions(load_agent(args.agent))
    if not funcs:
        print("ツールがつながっていません。my_agent/agent.py の tools=[...] に関数を入れてください。")
        return
    if args.tool is None:
        for func in funcs.values():
            describe(func)
        return
    if args.tool not in funcs:
        fail(f"{args.tool} というツールはありません。つないであるのは {list(funcs)} です。")
    print(f"[ツール] {args.tool}({', '.join(repr(a) for a in args.args)})")
    result = call(funcs[args.tool], args.args)
    # ADK は dict 以外の戻り値を {"result": ...} に包んでLLMに渡す
    show_response(result if isinstance(result, dict) else {"result": result})


if __name__ == "__main__":
    run(main)
