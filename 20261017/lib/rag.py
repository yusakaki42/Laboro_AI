"""QAの登録と検索（触らない）。

register() で data/ のCSVをすべて読み、ベクトルにして out/index.npz に保存する。
search() はその保存した索引から、質問に意味の近いQAを返す。
"""

import csv
import hashlib
import json
import os
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INDEX = ROOT / "out" / "index.npz"
MOCK_DIM = 512


class RagError(Exception):
    """索引がない、または今の設定と合わないときのエラー。メッセージはそのまま学生に見せる。"""


def is_mock() -> bool:
    return os.getenv("HANDSON_MOCK") == "1"


def api_key_name() -> str:
    return "OPENAI_API_KEY"


def embed_model() -> str:
    if is_mock():
        return "mock"
    return os.getenv("HANDSON_EMBED_MODEL", "text-embedding-3-small")


def qa_files(data: Path | None = None) -> list[Path]:
    return sorted((data or DATA).glob("*.csv"))


def load_qa(paths: list[Path]) -> list[dict]:
    """question, answer 列を持つCSVを読み、空行を除いて返す。"""
    rows = []
    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                q, a = (row.get("question") or "").strip(), (row.get("answer") or "").strip()
                if q and a:
                    rows.append({"question": q, "answer": a, "source": path.name})
    return rows


def _fingerprint(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in paths:
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def _mock_embed(text: str) -> np.ndarray:
    """APIを使わない代わりの埋め込み。2文字単位の出現をハッシュで数える。"""
    v = np.zeros(MOCK_DIM)
    for i in range(len(text) - 1):
        v[zlib.crc32(text[i:i + 2].encode()) % MOCK_DIM] += 1
    return v


def _openai_embed(texts: list[str]) -> list[list[float]]:
    """OpenAIの埋め込みAPIでベクトルにする。認証は OPENAI_API_KEY を使う。"""
    from openai import OpenAI

    res = OpenAI().embeddings.create(model=embed_model(), input=texts)
    return [d.embedding for d in res.data]


def embed(texts: list[str]) -> np.ndarray:
    """文章をベクトルにする。長さ1に正規化して返す。"""
    if is_mock():
        vectors = np.array([_mock_embed(t) for t in texts])
    else:
        vectors = np.array(_openai_embed(texts))
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


def register(data: Path | None = None, index: Path | None = None) -> dict:
    """data/ のCSVをすべてベクトルにして保存する。ファイルごとの件数を返す。"""
    data, index = data or DATA, index or INDEX
    paths = qa_files(data)
    rows = load_qa(paths)
    if not rows:
        raise RagError(f"{data} に登録できるQAがありません。question,answer の2列のCSVを置いてください。")
    vectors = embed([f"{r['question']}\n{r['answer']}" for r in rows])
    meta = {
        "model": embed_model(),
        "fingerprint": _fingerprint(paths),
        "files": [p.name for p in paths],
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    index.parent.mkdir(parents=True, exist_ok=True)
    np.savez(index, vectors=vectors, rows=json.dumps(rows, ensure_ascii=False), meta=json.dumps(meta))
    counts = {p.name: 0 for p in paths}
    for r in rows:
        counts[r["source"]] += 1
    return {"counts": counts, **meta}


class Index:
    def __init__(self, rows: list[dict], vectors: np.ndarray, meta: dict):
        self.rows, self.vectors, self.meta = rows, vectors, meta

    @classmethod
    def load(cls, index: Path | None = None) -> "Index":
        index = index or INDEX
        if not index.exists():
            raise RagError("QAがまだ登録されていません。先に python register.py を実行してください。")
        with np.load(index) as z:
            rows, meta, vectors = json.loads(str(z["rows"])), json.loads(str(z["meta"])), z["vectors"]
        if meta["model"] != embed_model():
            raise RagError(
                f"登録したときの埋め込み（{meta['model']}）と今の設定（{embed_model()}）が違います。"
                "python register.py をやり直してください。"
            )
        return cls(rows, vectors, meta)

    def is_stale(self, data: Path | None = None) -> bool:
        """登録したあとに data/ のCSVが変わっていれば True。"""
        return self.meta["fingerprint"] != _fingerprint(qa_files(data))

    def search(self, query: str, k: int = 3) -> list[dict]:
        scores = self.vectors @ embed([query])[0]
        top = np.argsort(scores)[::-1][:k]
        return [{**self.rows[i], "score": round(float(scores[i]), 3)} for i in top]


def search(query: str, k: int = 3) -> list[dict]:
    """登録したQAから、query に意味の近いものを k 件返す。

    戻り値の例: [{"question": "...", "answer": "...", "source": "my_qa.csv", "score": 0.82}, ...]
    """
    return Index.load().search(query, k)
