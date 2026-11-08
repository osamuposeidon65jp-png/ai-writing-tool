# ✍️ AIライティングツール

Python + Streamlit + Gemini API で作った、個人用のオールインワン AI ライティングツールです。

## 機能

| 機能 | 内容 |
| --- | --- |
| 📝 ブログ記事作成 | テーマ・キーワード・読者・トーン・文字数から SEO を意識した記事を生成（構成案のみも可） |
| ✉️ メール返信作成 | 受信メールと伝えたい要点から、関係性・トーンに合った返信文を複数案作成 |
| 📄 文章要約 | テキスト / txt・md・pdf ファイルを、箇条書き・3行まとめなど形式を選んで要約 |
| 🔍 校正・リライト | 誤字脱字チェック、読みやすくリライト、トーン変換、文章の増量・短縮 |
| 📱 SNS投稿作成 | X / Instagram / LinkedIn / Facebook / Threads 向けの投稿文を複数パターン作成 |
| 💡 タイトル・キャッチコピー | 記事タイトル、キャッチコピー、メール件名などのアイデア出し |
| 🌐 翻訳 | 7言語・4スタイルで自然な翻訳 |
| 🕘 生成履歴 | セッション中の生成結果を一覧表示・一括ダウンロード |

全機能共通で、ストリーミング表示・文字数表示・コピー・Markdown ダウンロードに対応しています。
サイドバーのモデル一覧は、入力した API キーで利用可能なモデルを自動取得して表示します。

## セットアップ

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # .env に GEMINI_API_KEY を記入
streamlit run app.py
```

API キーは [Google AI Studio](https://aistudio.google.com/apikey) で取得できます。
`.env` を作らずに、アプリのサイドバーから直接入力することもできます。

## ファイル構成

- `app.py` … Streamlit の画面と各機能
- `prompts.py` … 各機能のプロンプトテンプレート（出力の質を調整したいときはここを編集）
- `gemini_client.py` … Gemini API 呼び出し
