import os
import requests

def generate_reply(prompt: str, context: str = "") -> str:
    prompt = (prompt or "")[:1000]
    context = (context or "")[:1200]
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Please use the in-app message to ask the seller your question about this product."
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            "messages": [
                {"role": "system", "content": "You are a helpful shopping assistant. Provide concise guidance based on product info and order policies. Encourage the user to message the seller using the in-app messaging for product-specific and order-specific questions. Do not ask for or share personal contact details. Do not provide payment links."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{prompt}"},
            ],
            "max_tokens": 256,
            "temperature": 0.3,
        }
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=15)
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Sorry, I couldn't generate a response right now. Please try again or message the seller directly."
