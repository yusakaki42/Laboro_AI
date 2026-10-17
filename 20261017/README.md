# 42 Tokyo AIエージェント開発ハンズオン（2026年10月17日）

ハンズオンで使うリポジトリです。QAを登録して検索し（S5）、その検索をツールにしてエージェントにつなぎます（S6）。回答はファイルに残せます（S7、S8）。

## 当日の流れ

コマンドは、S1でコンテナの中に入ったあと、すべてコンテナの中で打ちます（S3の説明ページを開くときだけ、コンテナの外）。ステップごとの詳しい手順は [docs/schedule.md](docs/schedule.md) にあります。

| 時刻 | ステップ | あなたがすること | 使うコマンドとファイル |
| :-- | :-- | :-- | :-- |
| 14:00 | チーム分け・確認 | 自分のチームを確かめ、チームの席に着く | |
| 14:10 | S1 オープニング・環境準備 | リポジトリを取得してビルドを始める（5〜15分）。待つあいだに趣旨を聞き、チームで自己紹介する。ビルドが終わったらコンテナの中に入り、エージェントが返事をするかを確かめる | 下の「準備」のコマンド<br>`python ask.py "こんにちは"` |
| 14:30 | S2 お題とデモ | 42 Tokyoをお客さんに見立て、42 Tokyoの魅力を答える営業エージェントを作る、というお題を聞く。司会のPCで、できあがったエージェントの動きを見る | |
| 14:40 | S3 仕組みの説明 | 説明ページを開き、LLM、ベクトル検索、RAG、Function calling、AIエージェントの話を聞く。ページの「ためしてみる」を押しながら聞く | コンテナの外で `xdg-open docs/shikumi.html`（ファイルをブラウザにドラッグしてもよい） |
| 14:55 | S4 QAを書く | 全員共通の3問に、42 Tokyoの営業担当として本当に答えるつもりで、自分の答えを書く。時間が余ったら、自由にQAを足してもよい。個人情報、ほかの人の名前、勤め先の名前は書かない | `data/my_qa.csv`（書き方は [data/README.md](data/README.md)） |
| 15:15 | S5 登録して検索する | 書いたQAを登録して検索し、どのQAが何点で返るか、言い回しを変えても引けるかを試す。15:25ごろ固有QAを足し、登録し直して、合言葉の質問で `secret_qa.csv` が1位に出るかを確かめる | `python register.py`（`data/` のCSVをすべて登録する）<br>`python search.py "質問"`（上位3件を、点数、ファイル名、答えの書き出しつきで出す）<br>`cp ops/sample_secret_qa.csv data/secret_qa.csv`（固有QAを足す） |
| 15:45 | 休憩 | | |
| 15:55 | S6 ツールを作る | `my_agent/agent.py` のTODOとADKのドキュメント（[Function tools](https://adk.dev/tools-custom/function-tools/)）を読み、検索をツールにしてエージェントにつなぐ。まず関数だけを呼んで戻り値を確かめ、それからエージェントに聞く。早く終わったら [発展課題](docs/challenges.md) に進む | `my_agent/agent.py`（作り変える）<br>`python try_tool.py`（つないだツールと、LLMに見えている説明を出す）<br>`python try_tool.py ツール名 引数`（LLMを通さずに関数だけを呼ぶ）<br>`python ask.py "質問"`（[1] 呼んだツール、[2] 引けた資料、[3] 回答の3段で出る） |
| 16:55 | S7 判定する | 1回だけ聞いて、回答をチームで見せ合う。話し合う回答を2〜3個選び、公式サイトに載せてよいかを、一人ずつOKかNGかと理由を言って話し合う | `python ask.py --save "42 Tokyoで学ぶと、どんな力が身につきますか？"`（回答を `out/answers.jsonl` に追記する） |
| 17:10 | S8 再度同じ質問をエージェントに聞いてみる | S7と同じ質問をもう一度だけ聞き、前の回答と見比べて、変わったところをチームに一言ずつ伝える。判定はしない | S7と同じコマンド。前の回答は、ターミナルを上にスクロールして見る |
| 17:25 | S9 総括 | 「次に何かを作るとき、最初に誰と何を決めるか」を一人1文、チームで言う | |
| 17:35 | S10 交流 | アンケートに答え、後片付けをしてから、社員と話す。19:00まで | 下の「後片付け」のコマンド |

`lib/` の中のファイル（QAの登録と検索、モデルの呼び出し、エージェントの実行）は触りません。S6では、`lib/rag.py` の `search(query, k)` を使います。

キーが設定されていないときや、QAを登録する前に検索したときは、次に何をすればよいかを表示して止まります。CSVを書き直したら、もう一度 `python register.py` を実行してください。

## 準備

```bash
git clone https://github.com/laboroai/LaboroPublic42Events.git
cd LaboroPublic42Events/20261017
cp .env.example .env
nano .env              # OPENAI_API_KEY= のあとに、Discordで配るキーを貼る
docker compose build   # 5〜15分かかる
docker compose up -d   # コンテナを起動して、動かしたままにする
docker compose exec app bash   # コンテナの中に入る
```

コンテナの中に入ると、プロンプトが `root@...:/app#` に変わります。ここから先のコマンドは、すべてこの中で打ちます。PCを再起動したときやターミナルを閉じたときは、`docker compose up -d` と `docker compose exec app bash` をもう一度実行します。

キーがなくても `.env` に `HANDSON_MOCK=1` と書けば、APIを呼ばずに動きを試せます。

イメージは教室PC（x86_64）向けに作ります。Apple SiliconのMacで試すときは、`HANDSON_PLATFORM=linux/arm64 docker compose build` で作ってください。

## 後片付け（S10）

コンテナが作ったファイルは、教室PCのアカウントでは消せないので、先にコンテナで消します。コンテナの中にいるときは、`exit` で抜けてから実行します。

```bash
docker compose exec app sh -c 'rm -rf out .pytest_cache .mypy_cache && find . -name __pycache__ -prune -exec rm -rf {} +'
docker compose down --rmi all
cd ../.. && rm -rf LaboroPublic42Events
```

書いたQA、保存した回答、キーを書いた `.env`、ビルドしたイメージがすべて消えます。

## 動作確認

キーがなくても、コンテナの中で次のコマンドを実行すると、一通りの動きを確かめられます（試験はAPIを呼ばない）。

```bash
pytest -q
```
