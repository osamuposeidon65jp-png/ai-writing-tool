"""各機能のシステム指示とプロンプトテンプレート"""

BASE_SYSTEM = (
    "あなたは日本語のプロのライター兼編集者です。"
    "読みやすく、自然で、正確な日本語で出力してください。"
    "出力は Markdown 形式で、前置きや「承知しました」などの挨拶は不要です。"
)


def blog_prompt(theme, keywords, target, tone, length, outline_only, extra):
    task = "記事の構成案（見出し構成と各見出しで書く内容の要点）だけ" if outline_only else "記事本文"
    return f"""以下の条件でブログ記事の{task}を作成してください。

# 条件
- テーマ: {theme}
- 含めたいキーワード: {keywords or "特になし"}
- 想定読者: {target or "一般読者"}
- 文体・トーン: {tone}
- 目安の文字数: 約{length}文字
- 追加の要望: {extra or "特になし"}

# 出力ルール
- 冒頭に魅力的な記事タイトル案を1つ（# 見出し）
- 導入文で読者の悩みや関心に触れる
- H2/H3 見出しで論理的に構成する
- キーワードは不自然にならない範囲で盛り込む（SEOを意識）
- 最後にまとめを入れる
"""


def email_prompt(received, points, relation, tone, variations, signature):
    return f"""以下の受信メールに対する返信文を作成してください。

# 受信メール
{received}

# 返信で伝えたい要点
{points or "受信内容に対して適切に返答する"}

# 条件
- 相手との関係: {relation}
- トーン: {tone}
- 作成する案の数: {variations}案（それぞれ「## 案1」のように見出しをつける）
- 署名: {signature or "（署名なし）"}

# 出力ルール
- 各案に適切な件名（Re: ～）を付ける
- 日本のビジネスマナーに沿った自然な言い回しにする
- 相手の質問や依頼には漏れなく答える
"""


def summary_prompt(text, style, length, focus):
    return f"""以下の文章を要約してください。

# 要約形式
{style}

# 要約の長さ
{length}

# 特に注目してほしい観点
{focus or "特になし（全体をバランスよく）"}

# 対象の文章
\"\"\"
{text}
\"\"\"
"""


def proofread_prompt(text, mode, tone):
    if mode == "誤字脱字・文法チェック":
        instruction = (
            "文章の誤字脱字・文法の誤り・表記ゆれ・わかりにくい表現を指摘し、修正してください。\n"
            "出力は「## 修正後の文章」と「## 修正箇所一覧（修正前 → 修正後 / 理由）」の2部構成にしてください。"
        )
    elif mode == "リライト（読みやすく）":
        instruction = "意味を変えずに、より読みやすく伝わりやすい文章にリライトしてください。"
    elif mode == "トーン変換":
        instruction = f"意味を変えずに、文章のトーンを「{tone}」に変換してください。"
    elif mode == "文章を膨らませる":
        instruction = "内容を補足・具体化し、文章を約2倍の分量に膨らませてください。"
    else:  # 文章を短くする
        instruction = "要点を残したまま、文章を約半分の分量に簡潔にしてください。"

    return f"""{instruction}

# 対象の文章
\"\"\"
{text}
\"\"\"
"""


def sns_prompt(topic, platform, tone, count, hashtags, emoji):
    rules = {
        "X (旧Twitter)": "1投稿あたり全角140文字以内。冒頭で興味を引く。",
        "Instagram": "キャプションとして、改行を活用し読みやすく。最後にハッシュタグをまとめる。",
        "LinkedIn": "ビジネス向けに、専門性と学びが伝わる構成。",
        "Facebook": "親しみやすく、コメントしたくなる問いかけを入れる。",
        "Threads": "会話的でカジュアル。500文字以内。",
    }
    return f"""以下の内容で {platform} 向けの投稿文を{count}パターン作成してください。

# 投稿の内容・伝えたいこと
{topic}

# 条件
- トーン: {tone}
- プラットフォームのルール: {rules.get(platform, "")}
- ハッシュタグ: {"適切なものを3〜5個付ける" if hashtags else "付けない"}
- 絵文字: {"適度に使う" if emoji else "使わない"}
- 各パターンに「## パターン1」のように見出しをつける
"""


def title_prompt(content, kind, count):
    return f"""以下の内容に対して「{kind}」を{count}個提案してください。

# 内容
{content}

# 出力ルール
- 番号付きリストで出力する
- 方向性（数字を使う / 疑問形 / ベネフィット訴求 / 意外性 など）をバラけさせる
- 各案の後ろに（ ）で狙いを一言添える
"""


def translate_prompt(text, target_lang, style):
    return f"""以下の文章を{target_lang}に翻訳してください。

# 翻訳スタイル
{style}

# 出力ルール
- 翻訳文のみを出力する
- 固有名詞や専門用語は正確に扱う

# 対象の文章
\"\"\"
{text}
\"\"\"
"""
