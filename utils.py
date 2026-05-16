import openai
from db import get_faqs

def get_openai_answer(question, api_key):
    try:
        openai.api_key = api_key
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":question}],
            max_tokens=300,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # if OpenAI fails or key not provided, return None to trigger FAQ fallback
        return None
