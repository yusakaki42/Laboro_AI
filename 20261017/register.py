"""data/ のQAのCSVをすべて登録する（S5）。QAを書き直したら、もう一度実行する。

  python register.py
"""

from lib.cli import run
from lib.rag import register


def main():
    result = register()
    print(f"登録しました（埋め込み: {result['model']}）")
    for name, count in result["counts"].items():
        print(f"  {name:<16} {count}件")


if __name__ == "__main__":
    run(main)
