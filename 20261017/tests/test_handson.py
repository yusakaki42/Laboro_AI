"""HANDSON_MOCK=1 で、APIを呼ばずに配布物の動きを確かめる。

ツールをつないだエージェントの試験は、運営側で持つ。
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ["HANDSON_MOCK"] = "1"

import pytest

from lib import rag
from lib.runner import ask, load_agent

ROOT = Path(__file__).resolve().parent.parent
# 当日配る固有QA。S5で data/secret_qa.csv にコピーしてもらう
SECRET = ROOT / "ops" / "sample_secret_qa.csv"
SECRET_Q = "今日のハンズオンの合言葉は？"


@pytest.fixture
def data(tmp_path):
    """配布時の data/ に、学生のQAと当日配る固有QAを足した状態。"""
    d = tmp_path / "data"
    d.mkdir()
    (d / "my_qa.csv").write_text(
        "question,answer\n42の一番の魅力は？,仲間と教え合えること\n授業料はいくら？,無料\n", encoding="utf-8"
    )
    shutil.copy(SECRET, d / "secret_qa.csv")
    return d


@pytest.fixture
def index(data, tmp_path, monkeypatch):
    path = tmp_path / "out" / "index.npz"
    rag.register(data, path)
    monkeypatch.setattr(rag, "INDEX", path)
    monkeypatch.setattr(rag, "DATA", data)
    return path


def test_register_reads_every_csv_in_data(data, tmp_path):
    result = rag.register(data, tmp_path / "index.npz")
    assert result["counts"] == {"my_qa.csv": 2, "secret_qa.csv": 1}


def test_search_without_register_tells_what_to_do(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "INDEX", tmp_path / "none.npz")
    with pytest.raises(rag.RagError, match="register.py"):
        rag.search("授業料")


def test_search_returns_source_and_score(index):
    top = rag.search(SECRET_Q, k=1)[0]
    assert top["source"] == "secret_qa.csv"
    assert 0 < top["score"] <= 1


def test_search_shows_answers(index, monkeypatch, capsys):
    import search as search_cmd

    monkeypatch.setattr(sys, "argv", ["search.py", SECRET_Q])
    search_cmd.main()
    assert "答え: 今日の合言葉は" in capsys.readouterr().out


def test_index_built_in_another_mode_is_rejected(index, monkeypatch):
    monkeypatch.setenv("HANDSON_MOCK", "0")
    with pytest.raises(rag.RagError, match="register.py をやり直して"):
        rag.Index.load(index)


def test_editing_csv_after_register_is_detected(index, data):
    assert not rag.Index.load(index).is_stale(data)
    (data / "my_qa.csv").write_text("question,answer\n増やした,QA\n", encoding="utf-8")
    assert rag.Index.load(index).is_stale(data)


def test_template_agent_says_hello_without_tools():
    result = ask(load_agent("my_agent.agent"), "こんにちは")
    assert result["tool_calls"] == []
    assert "こんにちは" in result["answer"]


def _run(*args, env=None):
    return subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, **(env or {})},
    )


def test_commands_stop_with_a_message_when_key_is_missing():
    res = _run("search.py", "授業料", env={"HANDSON_MOCK": "0", "OPENAI_API_KEY": ""})
    assert res.returncode == 2
    assert "OPENAI_API_KEY" in res.stderr


def test_ask_saves_answer(tmp_path, monkeypatch):
    import ask as ask_cmd

    answers = tmp_path / "out" / "answers.jsonl"
    monkeypatch.setattr(ask_cmd, "ANSWERS", answers)
    monkeypatch.setattr(sys, "argv", ["ask.py", "--save", "こんにちは"])
    ask_cmd.main()
    record = json.loads(answers.read_text(encoding="utf-8").splitlines()[0])
    assert record["question"] == "こんにちは"
    assert record["agent"] == "my_agent.agent"
    assert record["tool_calls"] == []


def test_real_model_calls_openai(monkeypatch):
    from lib import model

    monkeypatch.setenv("HANDSON_MOCK", "0")
    monkeypatch.delenv("HANDSON_MODEL", raising=False)
    monkeypatch.delenv("HANDSON_REASONING_EFFORT", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    llm = model.get_model()
    assert llm.model == "openai/gpt-5.6-terra"
    assert "api_base" not in llm._additional_args
    assert "reasoning_effort" not in llm._additional_args


def test_real_embedding_uses_openai(monkeypatch):
    import openai

    calls = []

    class FakeEmbeddings:
        def create(self, model, input):
            calls.append((model, input))
            return SimpleNamespace(data=[SimpleNamespace(embedding=[3.0, 4.0]) for _ in input])

    monkeypatch.setenv("HANDSON_MOCK", "0")
    monkeypatch.delenv("HANDSON_EMBED_MODEL", raising=False)
    monkeypatch.setattr(openai, "OpenAI", lambda: SimpleNamespace(embeddings=FakeEmbeddings()))
    vectors = rag.embed(["42の魅力"])
    assert calls == [("text-embedding-3-small", ["42の魅力"])]
    assert vectors.tolist() == [[0.6, 0.8]]


def _try_tool(monkeypatch, capsys, *argv):
    import try_tool

    monkeypatch.setattr(sys, "argv", ["try_tool.py", *argv])
    try_tool.main()
    return capsys.readouterr().out


def test_try_tool_without_tools_tells_what_to_do(monkeypatch, capsys):
    assert "tools=[...]" in _try_tool(monkeypatch, capsys)


def test_try_tool_lists_what_the_llm_sees(monkeypatch, capsys):
    out = _try_tool(monkeypatch, capsys, "--agent", "tests.tool_agent")
    assert "[ツール] fake_search" in out
    assert "質問をそのまま" in out
    assert "引数: k（integer）" in out


def test_try_tool_calls_the_function_with_typed_args(monkeypatch, capsys):
    out = _try_tool(monkeypatch, capsys, "--agent", "tests.tool_agent", "fake_search", "合言葉", "2")
    assert out.count("0.500  test.csv") == 2


def test_try_tool_explains_missing_hits_for_text_results(monkeypatch, capsys):
    out = _try_tool(monkeypatch, capsys, "--agent", "tests.tool_agent", "plain_text", "合言葉")
    assert '"result": "結果: 合言葉"' in out
    assert "そのまま返すと表示されます" in out


def test_ask_shows_search_materials_and_answer_in_order(monkeypatch, capsys):
    import ask as ask_cmd

    monkeypatch.setattr(sys, "argv", ["ask.py", "--agent", "tests.tool_agent", "合言葉"])
    ask_cmd.main()
    out = capsys.readouterr().out
    assert out.index("[1] 調べる") < out.index("[2] 引けた資料") < out.index("[3] 回答")
    assert 'fake_search({"query": "合言葉"})' in out
    assert "答え: 試験" in out


def test_ask_without_tools_says_the_llm_answered_alone(monkeypatch, capsys):
    import ask as ask_cmd

    monkeypatch.setattr(sys, "argv", ["ask.py", "こんにちは"])
    ask_cmd.main()
    out = capsys.readouterr().out
    assert "もともと知っていることだけで答えました" in out
    assert "[2] 引けた資料" not in out
