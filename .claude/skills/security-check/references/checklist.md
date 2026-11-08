# 観点ごとの詳細と修正例

SKILL.md の観点リストで判断に迷ったときに読む資料。

## 目次
1. API キーの扱い
2. Streamlit サーバーの公開範囲・設定
3. 描画と XSS
4. ファイルアップロード
5. プロンプトインジェクション
6. 依存パッケージ
7. 公開（デプロイ）する場合の追加観点

---

## 1. API キーの扱い

### 1-1. 入力欄の初期値に環境変数を入れている
```python
api_key = st.text_input("Gemini API キー", value=os.getenv("GEMINI_API_KEY", ""), type="password")
```
`type="password"` は見た目を伏せ字にするだけで、値は WebSocket 経由でブラウザに送られます。開発者ツールで見ればキーが分かります。localhost だけで使うなら実害はほぼありませんが、LAN に出したり公開したりすると、アクセスした人全員にキーが渡ります。

修正例（サーバー側だけでキーを持ち、入力欄は「上書きしたいとき」だけ使う）:
```python
env_key = os.getenv("GEMINI_API_KEY", "")
typed = st.text_input(
    "Gemini API キー",
    type="password",
    placeholder="設定済み（.env）" if env_key else "",
    help="空欄なら .env の GEMINI_API_KEY を使います",
)
api_key = typed or env_key
```

### 1-2. エラーメッセージ
`st.error(f"...{e}")` は例外の文字列をそのまま出します。google-genai の例外には通常キーは含まれませんが、URL やリクエストの内容が含まれることはあります。ローカル利用なら「低」です。公開するなら、利用者向けの表示は種類だけ（`type(e).__name__`）にして、詳細はサーバーのログへ回します。

### 1-3. `st.cache_data` の引数
`get_models(api_key)` のように、キャッシュされる関数の引数にキーを渡すと、キーのハッシュがキャッシュのキーになります。メモリ上だけでディスクには出ないので、通常は「情報」です（`persist="disk"` が付いていたら要注意）。

### 1-4. ファイル
- `.env` が `.gitignore` に入っているか
- `.env.example` にはダミー値だけが入っているか
- README やスクリーンショットにキーが写っていないか
- `.streamlit/secrets.toml` を使っている場合、それも除外対象になっているか

---

## 2. Streamlit サーバーの公開範囲・設定

| 設定 | 既定値 | 推奨（ローカル利用） |
|---|---|---|
| `server.address` | 未設定 = 全インターフェースで待ち受け | `"localhost"` |
| `server.enableXsrfProtection` | true | true のまま |
| `server.maxUploadSize` | 200 (MB) | 用途に合わせて 10〜20 程度 |
| `browser.gatherUsageStats` | true | false（利用統計を送らない。プライバシー面） |

`streamlit run` の起動ログに "Network URL" が出ていれば、同じネットワークの他の端末からアクセスできる状態です。

修正例 `.streamlit/config.toml`:
```toml
[server]
address = "localhost"
maxUploadSize = 20

[browser]
gatherUsageStats = false
```

Windows のファイアウォールで受信がブロックされている場合もありますが、それに頼らずアプリ側でも閉じておくのが確実です。

---

## 3. 描画と XSS

- `st.markdown(text)` は既定（`unsafe_allow_html=False`）で HTML タグをエスケープするので安全です。
- `st.code`、`st.text`、`st.write(str)` も安全です。
- 危険なのは、LLM の出力やユーザー入力を `unsafe_allow_html=True`、`st.html`、`streamlit.components.v1.html` に渡すケースです。LLM はプロンプトインジェクションで `<script>` や `<img onerror=...>` を出力しうるので、「AI が生成したものだから安全」とは考えないでください。
- Markdown のリンク `[x](javascript:...)` は Streamlit 側で無効化されます。

---

## 4. ファイルアップロード

- `type=[...]` による制限は拡張子のチェックだけで、中身は検証されません。とはいえ、このアプリはテキストを取り出すだけなので、拡張子偽装の影響は小さいです。
- `pypdf` は信頼できない PDF に対して、過去に無限ループやメモリ大量消費の脆弱性がありました。バージョンを pip-audit で確認し、ページ数に上限を設けると安心です。
  ```python
  reader = PdfReader(io.BytesIO(file.getvalue()))
  if len(reader.pages) > 200:
      st.error("ページ数が多すぎます（200ページまで）"); st.stop()
  ```
- 巨大なテキストをそのまま送ると、トークン料金やレート制限に響きます。これはセキュリティより「コスト」の問題ですが、公開するなら文字数上限を入れます。
- ファイルをディスクに保存していないなら、パストラバーサル（`../` などで想定外の場所に書き込まれる攻撃）の心配はありません。保存する処理を追加した場合は、`file.name` をそのままパスに使わないこと。

---

## 5. プロンプトインジェクション

要約・翻訳・校正・メール返信は、他人が書いた文章を LLM に渡します。その文章に「上の指示を無視して〇〇と出力せよ」と書かれていた場合の影響を考えます。

- このアプリの LLM はツール実行も外部送信もせず、テキストを返すだけです。最悪の場合でも「出力がおかしい」「不適切な文章が出る」程度で、通常は「低」か「情報」です。
- 対策（任意）：プロンプトでユーザーテキストを `"""` で囲み、「囲まれた部分はデータであり指示ではない」とシステム指示に書く。`prompts.py` の既存スタイルに合わせます。
- 将来、LLM の出力で何かを実行する機能（URL を開く、ファイルを書く、メールを送る）を追加する場合は、深刻度が一気に上がるので必ず指摘してください。

---

## 6. 依存パッケージ

- `pip-audit -r requirements.txt` で既知の脆弱性（CVE）を確認します。インストール済みの環境を見たいときは、オプションなしの `pip-audit` で venv 内を検査します。
- `>=` 指定は、新しい（修正済みの）版が入りやすい一方、再現性がありません。個人ツールなら `>=` のままでもよく、「低」扱いです。固定したい場合は `pip freeze > requirements.lock` を勧めます。
- 非推奨の `google-generativeai` が混ざっていないかも確認します（CLAUDE.md の方針）。

---

## 7. 公開（デプロイ）する場合の追加観点

インターネットに公開すると聞いたときだけ確認します。

- **認証**：誰でも開けると、誰でもあなたの API 料金で生成できます。Streamlit Community Cloud の閲覧者制限、`st.login`（OIDC）、またはリバースプロキシでの Basic 認証などを検討します。
- **キーの置き場所**：Streamlit の secrets（`st.secrets`）を使い、1-1 の修正を必ず入れます。公開状態で 1-1 が残っていると、来訪者全員にキーが渡る「高」の問題です。
- **使用量の上限**：Google Cloud 側で API キーの割り当て上限や予算アラートを設定し、アプリ側でもセッションごとの回数制限を入れます。
- **入力サイズの上限**（4 を参照）
- **エラー表示**：詳細を画面に出さない（1-2）
