"""Streamlit + LLM API アプリ向けの静的セキュリティスキャナ（標準ライブラリのみ）

使い方:
    python scan.py <プロジェクトのルート>

見つかった秘密情報は先頭4文字以外を伏せて表示する（実際の値は絶対に出力しない）。
結果は「機械的に見つけた候補」なので、最終判断はコードを読んで行うこと。
"""

import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".venv", "venv", "env", "__pycache__", ".git", "node_modules", ".claude"}
TEXT_EXTS = {".py", ".toml", ".txt", ".md", ".json", ".yaml", ".yml", ".cfg", ".ini", ".example", ".sh", ".ps1", ".bat"}

SECRET_PATTERNS = [
    ("Google / Gemini API キー", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("Anthropic API キー", re.compile(r"sk-ant-[0-9A-Za-z_\-]{20,}")),
    ("OpenAI API キー", re.compile(r"sk-(?:proj-)?[0-9A-Za-z_\-]{32,}")),
    ("ハードコードされた秘密情報らしき代入",
     re.compile(r"""(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["'][^"'\s]{16,}["']""")),
]

CODE_PATTERNS = [
    ("高", "unsafe_allow_html=True（生成物やユーザー入力を HTML として描画すると XSS の恐れ）",
     re.compile(r"unsafe_allow_html\s*=\s*True")),
    ("高", "components.html / iframe（任意の HTML/JS を描画）", re.compile(r"components\.(v1\.)?(html|iframe)\s*\(")),
    ("中", "st.html（HTML を直接描画。入力元を確認）", re.compile(r"\bst\.html\s*\(")),
    ("高", "eval / exec", re.compile(r"(?<![\w.])(eval|exec)\s*\(")),
    ("高", "shell=True / os.system（コマンドインジェクションの恐れ）", re.compile(r"shell\s*=\s*True|os\.system\s*\(")),
    ("中", "subprocess の利用（引数に入力値が入らないか確認）", re.compile(r"\bsubprocess\.")),
    ("高", "pickle の読み込み（信頼できないデータで任意コード実行）", re.compile(r"pickle\.loads?\s*\(")),
    ("中", "yaml.load（SafeLoader 以外は危険）", re.compile(r"yaml\.load\s*\((?![^)]*SafeLoader)")),
    ("中", "環境変数の秘密情報をウィジェットの初期値にしている（値がブラウザに送られる）",
     re.compile(r"(text_input|text_area)\s*\([^)]*value\s*=\s*os\.(getenv|environ)", re.S)),
    ("低", "例外メッセージをそのまま画面表示（内部情報が出る可能性）",
     re.compile(r"st\.(error|exception|write)\s*\(\s*f?[\"'].*\{\s*e\s*\}")),
    ("情報", "ファイルアップロード（サイズ上限・形式チェックを確認）", re.compile(r"st\.file_uploader\s*\(")),
    ("情報", "HTTP リクエスト（宛先が入力値で決まらないか＝SSRF を確認）",
     re.compile(r"\b(requests|httpx|urllib\.request)\.(get|post|urlopen|request)\s*\(")),
]


def mask(value: str) -> str:
    return value[:4] + "*" * 8 + f"（{len(value)}文字）"


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and (path.suffix in TEXT_EXTS or path.name.startswith(".env")):
            yield path


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def scan_secrets(root: Path, out: list):
    out.append("## 1. 秘密情報の混入")
    found = False
    for path in iter_files(root):
        if path.name == ".env":
            continue  # .env は秘密を置く場所なので中身は検査しない（存在と除外設定だけ見る）
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                found = True
                rel = path.relative_to(root)
                out.append(f"- [高] {rel}:{line_of(text, m.start())} {label}: {mask(m.group(0))}")
    if not found:
        out.append("- 該当なし（.env 以外のファイルに API キーらしき文字列は見つからず）")


def scan_env(root: Path, out: list):
    out.append("\n## 2. .env と除外設定")
    env = root / ".env"
    gitignore = root / ".gitignore"
    ignored = False
    if gitignore.exists():
        lines = [l.strip() for l in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()]
        ignored = any(l in (".env", ".env*", "*.env", "/.env") for l in lines)
    out.append(f"- .env の存在: {'あり' if env.exists() else 'なし'}")
    out.append(f"- .gitignore で .env を除外: {'はい' if ignored else 'いいえ（要対応）'}")
    if (root / ".git").exists():
        try:
            tracked = subprocess.run(["git", "-C", str(root), "ls-files", ".env"],
                                     capture_output=True, text=True, timeout=10).stdout.strip()
            out.append(f"- .env が git 管理下: {'はい（高: 履歴から削除しキーを再発行）' if tracked else 'いいえ'}")
        except Exception as e:
            out.append(f"- git の確認に失敗: {type(e).__name__}")
    else:
        out.append("- git リポジトリではない（コミット経由の漏えいは現時点でなし）")
    for p in root.glob(".streamlit/secrets.toml"):
        out.append(f"- {p.relative_to(root)} あり: .gitignore で除外されているか確認")


def scan_code(root: Path, out: list):
    out.append("\n## 3. 危険なコードパターン（*.py）")
    found = False
    for path in iter_files(root):
        if path.suffix != ".py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for sev, label, pat in CODE_PATTERNS:
            for m in pat.finditer(text):
                found = True
                out.append(f"- [{sev}] {path.relative_to(root)}:{line_of(text, m.start())} {label}")
    if not found:
        out.append("- 該当なし")


def scan_streamlit_config(root: Path, out: list):
    out.append("\n## 4. Streamlit の設定")
    configs = [root / ".streamlit" / "config.toml", Path.home() / ".streamlit" / "config.toml"]
    merged = ""
    for c in configs:
        if c.exists():
            out.append(f"- 設定ファイル: {c}")
            merged += c.read_text(encoding="utf-8", errors="ignore") + "\n"
    if not merged:
        out.append("- 設定ファイルなし（すべて既定値）")
    m = re.search(r'^\s*address\s*=\s*"([^"]*)"', merged, re.M)
    if m and m.group(1) in ("localhost", "127.0.0.1"):
        out.append(f'- server.address = "{m.group(1)}"（ローカルのみで待ち受け: OK）')
    else:
        out.append("- [中] server.address が localhost ではない／未設定: 既定では全インターフェースで待ち受けるため、"
                   "同じネットワークの他人もアクセスできる")
    if re.search(r"enableXsrfProtection\s*=\s*false", merged):
        out.append("- [中] server.enableXsrfProtection = false（CSRF 対策が無効）")
    m = re.search(r"maxUploadSize\s*=\s*(\d+)", merged)
    out.append(f"- server.maxUploadSize = {m.group(1) + ' MB' if m else '未設定（既定 200 MB）'}")


def scan_requirements(root: Path, out: list):
    out.append("\n## 5. 依存パッケージ")
    req = root / "requirements.txt"
    if not req.exists():
        out.append("- requirements.txt なし")
        return
    for line in req.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        pinned = "==" in line
        out.append(f"- {line}  {'(固定)' if pinned else '[低] バージョン未固定'}")
    out.append("- 既知の脆弱性は pip-audit で別途確認すること（このスクリプトはネットワークに出ない）")


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    out = [f"# 静的スキャン結果: {root}\n"]
    for step in (scan_secrets, scan_env, scan_code, scan_streamlit_config, scan_requirements):
        try:
            step(root, out)
        except Exception as e:  # 1項目の失敗で全体を止めない
            out.append(f"- （{step.__name__} の実行に失敗: {type(e).__name__}: {e}）")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
