"""登録したQAを検索する（S5）。どのQAが何点で返るかを、答えの書き出しとあわせて表示する。

  python search.py "42の魅力は？"
  python search.py -k 5 "授業料"
"""

import argparse

from lib.cli import print_hits, run
from lib.rag import Index


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query")
    parser.add_argument("-k", type=int, default=3, help="返す件数")
    args = parser.parse_args()

    index = Index.load()
    if index.is_stale():
        print("[注意] 登録したあとにCSVが変わっています。python register.py をやり直してください。\n")
    print(f"「{args.query}」に近いQA（点数は1に近いほど近い）")
    print_hits(index.search(args.query, args.k), answers=True)


if __name__ == "__main__":
    run(main)
