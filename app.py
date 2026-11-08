"""AIライティングツール（Streamlit + Gemini API）"""

import io
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

import prompts
from gemini_client import list_models, stream_generate

load_dotenv()

st.set_page_config(page_title="AIライティングツール", page_icon="✍️", layout="wide")

# API からモデル一覧を取得できなかったときの候補
DEFAULT_MODELS = ["gemini-3.8-flash"]
PREFERRED_MODEL = "gemini-3.8-flash"


@st.cache_data(ttl=3600, show_spinner=False)
def get_models(api_key: str) -> list[str]:
    """利用可能なモデル一覧（1時間キャッシュ）。取得失敗時は既定の候補を返す"""
    try:
        return list_models(api_key) or DEFAULT_MODELS
    except Exception:
        return DEFAULT_MODELS

FEATURES = {
    "📝 ブログ記事作成": "blog",
    "✉️ メール返信作成": "email",
    "📄 文章要約": "summary",
    "🔍 校正・リライト": "proofread",
    "📱 SNS投稿作成": "sns",
    "💡 タイトル・キャッチコピー": "title",
    "🌐 翻訳": "translate",
    "🕘 生成履歴": "history",
}

if "history" not in st.session_state:
    st.session_state.history = []


# ---------------------------------------------------------------- サイドバー
with st.sidebar:
    st.title("✍️ AIライティングツール")
    feature_label = st.radio("機能を選択", list(FEATURES.keys()))
    feature = FEATURES[feature_label]

    st.divider()
    st.subheader("⚙️ 設定")
    # .env のキーはサーバー側だけで保持し、ブラウザには送らない
    env_key = os.getenv("GEMINI_API_KEY", "")
    typed_key = st.text_input(
        "Gemini API キー",
        type="password",
        placeholder="設定済み（.env）" if env_key else "",
        help="空欄なら .env の GEMINI_API_KEY を使います。入力するとそちらが優先されます",
    )
    api_key = typed_key or env_key
    models = get_models(api_key) if api_key else DEFAULT_MODELS
    default_index = models.index(PREFERRED_MODEL) if PREFERRED_MODEL in models else 0
    model = st.selectbox(
        "モデル", models, index=default_index,
        help="API キーで利用できるモデルを自動で取得しています",
    )
    temperature = st.slider(
        "創造性 (temperature)", 0.0, 2.0, 0.7, 0.1,
        help="低いほど安定・正確、高いほど多様で創造的な出力になります",
    )


# ---------------------------------------------------------------- 共通処理
def run(prompt: str, title: str) -> None:
    """プロンプトを送信し、結果をストリーミング表示して履歴に保存する"""
    if not api_key:
        st.error("サイドバーで Gemini API キーを入力してください。")
        return

    st.subheader("✨ 生成結果")
    try:
        with st.container(border=True):
            result = st.write_stream(
                stream_generate(api_key, model, prompt, prompts.BASE_SYSTEM, temperature)
            )
    except Exception as e:  # API キー不正・レート制限など
        st.error(f"生成中にエラーが発生しました: {e}")
        return

    st.session_state.history.insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "feature": feature_label,
        "title": title,
        "result": result,
    })
    st.session_state[f"last_{feature}"] = result
    show_actions(result, key="new")


def show_actions(result: str, key: str) -> None:
    """コピー用テキスト・文字数・ダウンロードボタンを表示する"""
    st.caption(f"文字数: {len(result):,} 文字")
    with st.expander("📋 コピー用（右上のアイコンでコピー）"):
        st.code(result, language="markdown")
    st.download_button(
        "💾 Markdown でダウンロード",
        data=result,
        file_name=f"{feature}_{datetime.now():%Y%m%d_%H%M%S}.md",
        mime="text/markdown",
        key=f"dl_{feature}_{key}",
    )


def show_last_result() -> None:
    """ボタンを押していない再描画時でも、直前の結果を残しておく"""
    last = st.session_state.get(f"last_{feature}")
    if last:
        st.subheader("✨ 前回の生成結果")
        with st.container(border=True):
            st.markdown(last)
        show_actions(last, key="last")


def read_uploaded_file(file) -> str:
    """アップロードされた txt / md / pdf からテキストを取り出す"""
    if file.name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file.getvalue()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return file.getvalue().decode("utf-8", errors="ignore")


# ---------------------------------------------------------------- 各機能
st.header(feature_label)

if feature == "blog":
    st.write("テーマと条件を入れるだけで、SEO を意識したブログ記事を作成します。")
    theme = st.text_input("記事のテーマ *", placeholder="例: 在宅ワークで集中力を保つコツ")
    col1, col2 = st.columns(2)
    with col1:
        keywords = st.text_input("含めたいキーワード", placeholder="例: 在宅ワーク, 集中力, ポモドーロ")
        target = st.text_input("想定読者", placeholder="例: リモートワークを始めたばかりの会社員")
    with col2:
        tone = st.selectbox("文体・トーン", ["です・ます調（丁寧）", "だ・である調", "カジュアル・親しみやすい", "専門的・論理的"])
        length = st.select_slider("目安の文字数", [1000, 2000, 3000, 4000, 5000], value=3000)
    extra = st.text_area("追加の要望（任意）", placeholder="例: 体験談風に、最後に行動を促す一文を入れて")
    outline_only = st.checkbox("まずは構成案だけ作る")

    if st.button("記事を生成する", type="primary", disabled=not theme):
        run(prompts.blog_prompt(theme, keywords, target, tone, length, outline_only, extra), theme)
    else:
        show_last_result()

elif feature == "email":
    st.write("受け取ったメールを貼り付けると、状況に合った返信文を考えます。")
    received = st.text_area("受信したメール *", height=200)
    points = st.text_area("返信で伝えたいこと（任意）", placeholder="例: 日程は来週火曜なら可能。資料は金曜までに送付する。")
    col1, col2, col3 = st.columns(3)
    with col1:
        relation = st.selectbox("相手との関係", ["取引先・顧客", "社内の上司", "社内の同僚", "初対面の相手", "友人・知人"])
    with col2:
        tone = st.selectbox("トーン", ["丁寧・フォーマル", "標準的なビジネス", "やわらかめ", "カジュアル"])
    with col3:
        variations = st.number_input("作成する案の数", 1, 3, 2)
    signature = st.text_input("署名（任意）", placeholder="例: 株式会社〇〇 山田")

    if st.button("返信文を作成する", type="primary", disabled=not received):
        run(prompts.email_prompt(received, points, relation, tone, variations, signature), received[:30])
    else:
        show_last_result()

elif feature == "summary":
    st.write("長い文章やファイルの内容を、目的に合わせて要約します。")
    file = st.file_uploader("ファイルから読み込む（txt / md / pdf）", type=["txt", "md", "pdf"])
    text = read_uploaded_file(file) if file else ""
    text = st.text_area("要約したい文章 *", value=text, height=250)
    st.caption(f"入力文字数: {len(text):,} 文字")
    col1, col2 = st.columns(2)
    with col1:
        style = st.selectbox("要約形式", ["箇条書き", "3行まとめ", "段落（文章）", "見出し付きの構造化要約", "結論 → 理由 → 詳細"])
    with col2:
        length = st.selectbox("要約の長さ", ["短く（100文字程度）", "標準（300文字程度）", "詳しく（600文字程度）"], index=1)
    focus = st.text_input("注目してほしい観点（任意）", placeholder="例: 決定事項とToDoを中心に")

    if st.button("要約する", type="primary", disabled=not text):
        run(prompts.summary_prompt(text, style, length, focus), text[:30])
    else:
        show_last_result()

elif feature == "proofread":
    st.write("誤字脱字チェック、読みやすいリライト、トーン変換などを行います。")
    text = st.text_area("対象の文章 *", height=250)
    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("処理内容", ["誤字脱字・文法チェック", "リライト（読みやすく）", "トーン変換", "文章を膨らませる", "文章を短くする"])
    with col2:
        tone = st.selectbox(
            "変換後のトーン（トーン変換時）",
            ["丁寧なビジネス文", "カジュアル", "やさしい（子ども向け）", "熱意のある・情熱的", "論理的・客観的"],
            disabled=mode != "トーン変換",
        )

    if st.button("実行する", type="primary", disabled=not text):
        run(prompts.proofread_prompt(text, mode, tone), f"{mode}: {text[:20]}")
    else:
        show_last_result()

elif feature == "sns":
    st.write("伝えたい内容から、各 SNS に最適化した投稿文を作成します。")
    topic = st.text_area("投稿したい内容 *", placeholder="例: ブログで在宅ワークの集中術の記事を公開した告知")
    col1, col2, col3 = st.columns(3)
    with col1:
        platform = st.selectbox("プラットフォーム", ["X (旧Twitter)", "Instagram", "LinkedIn", "Facebook", "Threads"])
    with col2:
        tone = st.selectbox("トーン", ["親しみやすい", "プロフェッショナル", "ユーモアのある", "エモーショナル"])
    with col3:
        count = st.number_input("パターン数", 1, 5, 3)
    hashtags = st.checkbox("ハッシュタグを付ける", value=True)
    emoji = st.checkbox("絵文字を使う", value=True)

    if st.button("投稿文を作成する", type="primary", disabled=not topic):
        run(prompts.sns_prompt(topic, platform, tone, count, hashtags, emoji), f"{platform}: {topic[:20]}")
    else:
        show_last_result()

elif feature == "title":
    st.write("記事タイトル・キャッチコピー・メール件名などのアイデアを大量に出します。")
    content = st.text_area("内容・概要 *", placeholder="例: 30代向けの初心者向け資産運用の始め方を解説する記事")
    col1, col2 = st.columns(2)
    with col1:
        kind = st.selectbox("作りたいもの", ["ブログ記事タイトル", "キャッチコピー", "メールの件名", "YouTube動画タイトル", "商品名・サービス名"])
    with col2:
        count = st.slider("案の数", 3, 20, 10)

    if st.button("アイデアを出す", type="primary", disabled=not content):
        run(prompts.title_prompt(content, kind, count), f"{kind}: {content[:20]}")
    else:
        show_last_result()

elif feature == "translate":
    st.write("文章を自然な表現で翻訳します。")
    text = st.text_area("翻訳したい文章 *", height=250)
    col1, col2 = st.columns(2)
    with col1:
        target_lang = st.selectbox("翻訳先の言語", ["英語", "日本語", "中国語（簡体字）", "韓国語", "スペイン語", "フランス語", "ドイツ語"])
    with col2:
        style = st.selectbox("翻訳スタイル", ["自然な意訳", "原文に忠実な直訳", "ビジネス向けのフォーマルな表現", "カジュアルな会話調"])

    if st.button("翻訳する", type="primary", disabled=not text):
        run(prompts.translate_prompt(text, target_lang, style), f"{target_lang}: {text[:20]}")
    else:
        show_last_result()

elif feature == "history":
    st.write("このセッションで生成した結果の一覧です（ブラウザを再読み込みすると消えます）。")
    history = st.session_state.history
    if not history:
        st.info("まだ生成履歴はありません。")
    else:
        if st.button("🗑️ 履歴をすべて削除"):
            st.session_state.history = []
            st.rerun()
        all_md = "\n\n---\n\n".join(
            f"# {h['feature']} / {h['title']}\n_{h['time']}_\n\n{h['result']}" for h in history
        )
        st.download_button("💾 全履歴を Markdown でダウンロード", all_md, "history.md", "text/markdown")
        for i, h in enumerate(history):
            with st.expander(f"{h['time']}　{h['feature']}　{h['title']}"):
                st.markdown(h["result"])
                st.code(h["result"], language="markdown")
