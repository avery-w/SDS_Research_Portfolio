import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatBotService:
    SYSTEM_PROMPT = (
        "You are a helpful marketplace assistant. If a user asks specific questions "
        "about a product's condition or shipping details, encourage them to use the "
        "'Message Seller' feature to contact the merchant directly."
    )

    @staticmethod
    def get_response(user_message: str, product_description: str = None) -> str:
        messages = [{"role": "system", "content": ChatBotService.SYSTEM_PROMPT}]
        
        context = user_message
        if product_description:
            context = f"Product Context: {product_description}\n\nUser Question: {user_message}"
            
        messages.append({"role": "user", "content": context})
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I'm sorry, I'm having trouble connecting to my brain right now. Error: {str(e)}"
