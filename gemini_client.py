"""Gemini API の呼び出しをまとめたモジュール"""

from typing import Iterator

from google import genai
from google.genai import types


def list_models(api_key: str) -> list[str]:
    """API キーで利用できる、文章生成対応モデル名の一覧を返す"""
    client = genai.Client(api_key=api_key)
    names = [
        m.name.removeprefix("models/")
        for m in client.models.list()
        if "generateContent" in (m.supported_actions or [])
    ]
    return sorted(names, reverse=True)


def stream_generate(
    api_key: str,
    model: str,
    prompt: str,
    system_instruction: str,
    temperature: float = 0.7,
) -> Iterator[str]:
    """Gemini に問い合わせ、生成テキストを少しずつ返すジェネレーター"""
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=prompt,
        config=config,
    ):
        if chunk.text:
            yield chunk.text
