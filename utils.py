import os

from openai import OpenAI
from db import get_faqs


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _build_faq_context():
    faqs = get_faqs()
    if not faqs:
        return "No saved FAQs are available yet."
    return "\n".join(
        f"Q: {row.get('question', '')}\nA: {row.get('answer', '')}"
        for row in faqs[:20]
    )


def get_groq_answer(question, api_key=None, model=None):
    api_key = api_key or os.getenv("GROQ_API_KEY")
    model = model or os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL
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
