import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

SYSTEM_PROMPT = """You are the marketplace assistant. Help customers with product and order questions using only the provided context. Never share private data. Encourage contacting the seller via in-app messaging when questions require seller confirmation, availability, or customizations. Keep answers concise."""

def chatbot_reply(user_msg, context):
    model = os.getenv('OPENAI_MODEL','gpt-4o-mini')
    msgs = [
      {"role":"system","content": SYSTEM_PROMPT},
      {"role":"user","content": f"Context:\n{context}\n\nCustomer question:\n{user_msg}\n\nIf appropriate, suggest 'Use Message Seller to ask directly.'"}
    ]
    r = client.chat.completions.create(model=model, messages=msgs, temperature=0.3)
    return r.choices[0].message.content.strip()
