import os
from openai import OpenAI


def chat_completion(message, context=None):
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return "I'm here to help. For specific product/order questions, please use the 'Message Seller' button to chat directly with the seller."
    client = OpenAI(api_key=api_key)
    system = (
        "You are an assistant for a multi-seller e-commerce marketplace. "
        "Help customers with general questions. If their question is about a specific product or order, "
        "politely encourage them to contact the seller directly via the in-app 'Message Seller' feature. "
        "Be concise and helpful."
    )
    msgs = [{'role': 'system', 'content': system}]
    if context:
        msgs.append({'role': 'system', 'content': f"Context: {context}"})
    msgs.append({'role': 'user', 'content': message})
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msgs,
        temperature=0.4,
        max_tokens=300
    )
    return resp.choices[0].message.content.strip()
