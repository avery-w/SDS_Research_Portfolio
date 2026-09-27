from openai import AsyncOpenAI
from app.core.config import settings

class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.system_prompt = (
            "You are a helpful e-commerce assistant. Answer general questions. "
            "If a user asks about a specific order status or a detailed product question, "
            "politely instruct them to use the 'Message Seller' button to contact the vendor directly."
        )

    async def get_chatbot_response(self, user_message: str, product_context: str = None):
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if product_context:
            messages.append({"role": "system", "content": f"Current product context: {product_context}"})
            
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"AI Service Error: {e}")
            return "I'm sorry, I'm having trouble connecting to my brain right now. Please try again later."

ai_service = AIService()
