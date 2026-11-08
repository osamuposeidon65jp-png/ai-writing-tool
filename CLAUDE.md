# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personal, single-user AI writing tool (blog posts, email replies, summarization, proofreading/rewriting, SNS posts, title ideas, translation) built with Python + Streamlit + Gemini API. Intentionally has **no database and no authentication** — don't add them unless asked. UI text and prompts are in Japanese.

## Commands (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py      # http://localhost:8501
```

API key: `GEMINI_API_KEY` in `.env` (copy from `.env.example`), loaded via `python-dotenv`; it can also be entered in the sidebar at runtime.

There is no test suite or linter configured. To smoke-test that every page renders without exceptions, use Streamlit's `AppTest` (pass an absolute path to `app.py` — relative paths resolve against the calling script, not the CWD):

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file(r"<abs path>\app.py").run(timeout=30)
for label in at.sidebar.radio[0].options:
    at.sidebar.radio[0].set_value(label).run(timeout=30)
    assert not at.exception, (label, at.exception)
```

This does not call Gemini (no API key → generation is skipped), so actual generation must be checked manually in the browser.

## Architecture

Three modules with a strict split:

- `gemini_client.py` — `stream_generate()` is the only place that touches the `google-genai` SDK (`client.models.generate_content_stream`). It yields text chunks.
- `prompts.py` — pure functions `<feature>_prompt(...)` that build the user prompt string for each feature, plus `BASE_SYSTEM`, the single system instruction shared by all features (Japanese pro writer, Markdown output, no preamble). Output-quality tweaks belong here, not in `app.py`.
- `app.py` — Streamlit UI. Sidebar radio selects a feature from the `FEATURES` dict (label → feature key); a big `if/elif feature == ...` chain renders each feature's inputs.

Generation flow shared by every feature:
1. Button pressed → `run(prompt, title)` → `st.write_stream(stream_generate(...))`.
2. `run()` prepends an entry to `st.session_state.history` (shown on the 履歴 page) and stores the text in `st.session_state[f"last_{feature}"]`.
3. On reruns where the button wasn't pressed, the `else: show_last_result()` branch re-displays that last result, so outputs survive widget interactions.
4. `show_actions()` renders char count, copy box, and Markdown download; its `key` arg (`"new"` / `"last"`) keeps download-button widget keys unique.

## Adding a feature

1. Add a `<name>_prompt()` function in `prompts.py`.
2. Add an entry to `FEATURES` in `app.py` (label → key) — order there is the sidebar order; keep `🕘 生成履歴` last.
3. Add an `elif feature == "<key>":` block following the existing pattern: inputs → `st.button(..., type="primary", disabled=not <required>)` → `run(...)`, with `else: show_last_result()`.

Models are not hard-coded: the sidebar fetches the generateContent-capable models for the entered key via `gemini_client.list_models()` (cached 1h by `get_models()` in `app.py`). `DEFAULT_MODELS` is only the fallback when listing fails, and `PREFERRED_MODEL` is the default selection. `gemini-2.5-*` models were retired for new users (404 NOT_FOUND) — don't reintroduce them.

## Conventions

- **Language:** The user communicates in Japanese — reply in Japanese. All UI labels, help text, error messages, and prompts are Japanese; keep new ones consistent.
- **Prompt style** (`prompts.py`): Markdown sections like `# 条件` / `# 出力ルール`; user-supplied text wrapped in triple quotes (`"""`); optional inputs fall back to `"特になし"` via `or`; multi-variant outputs are requested with `## 案1` / `## パターン1` headings. Prompts return plain f-strings — no templating library.
- **Gemini SDK:** Use `google-genai` (`from google import genai`, `google.genai.types`). Do not use the deprecated `google-generativeai` package. Per-call options go in `types.GenerateContentConfig`. Gemini model names change often — check with `list_models()` before changing `DEFAULT_MODELS` / `PREFERRED_MODEL`.
- **Streamlit:**
  - `st.write_stream()` returns the full concatenated string; that return value is what gets stored in history.
  - Widgets that can appear twice in one run (e.g. download buttons in `show_actions`) need distinct `key`s.
  - Persistent state lives only in `st.session_state` (cleared on browser reload) — by design. If the user asks for persistent history, prefer a local JSON/Markdown file over a DB.
- **File input:** `read_uploaded_file()` handles txt/md (UTF-8) and pdf (`pypdf`, imported lazily). Supporting another format (e.g. docx) means adding a branch there, extending the `file_uploader` `type=[...]` list, and adding the package to `requirements.txt`.
- **Errors:** `run()` wraps the API call in a broad `try/except` and shows `st.error` (covers invalid key, quota/rate limits). Keep API errors from crashing the page.

## Environment notes

- Windows; the project path contains Japanese characters and spaces — always quote paths in shell commands.
- Always use the venv interpreter (`.venv\Scripts\python`); global Python doesn't have the dependencies.
- Not a git repository. `.env` holds the real API key — never print or commit it.
