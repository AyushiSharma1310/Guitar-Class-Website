import os
from pathlib import Path

from openai import OpenAI
from db import get_faqs


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
INDEX_PATH = Path(__file__).parent / "index.txt"


def _get_config_value(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


def _build_faq_context():
    context_parts = []
    if INDEX_PATH.exists():
        index_context = INDEX_PATH.read_text(encoding="utf-8").strip()
        if index_context:
            context_parts.append(f"Website FAQ knowledge base:\n{index_context}")

    faqs = get_faqs()
    if faqs:
        saved_faq_context = "\n".join(
            f"Q: {row.get('question', '')}\nA: {row.get('answer', '')}"
            for row in faqs[:20]
        )
        context_parts.append(f"Saved admin FAQs:\n{saved_faq_context}")

    if not context_parts:
        return "No saved FAQ context is available yet."
    return "\n\n".join(context_parts)


def get_groq_answer(question, api_key=None, model=None):
    api_key = api_key or _get_config_value("GROQ_API_KEY")
    model = model or _get_config_value("GROQ_MODEL") or DEFAULT_GROQ_MODEL
    if not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the helpful AI assistant for a guitar class website. "
                        "Answer using the saved FAQ context when it is relevant. "
                        "If the answer is not known, say so briefly and suggest using "
                        "the contact form."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Saved FAQ context:\n{_build_faq_context()}\n\nQuestion: {question}",
                },
            ],
            max_tokens=300,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # If Groq fails or no key is available, return None to trigger FAQ fallback.
        return None
