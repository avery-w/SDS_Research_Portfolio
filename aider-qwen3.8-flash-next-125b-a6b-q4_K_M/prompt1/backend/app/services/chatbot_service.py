import openai
from app.config import settings


class ChatbotService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.system_prompt = (
            "You are a helpful e-commerce marketplace assistant. "
            "You help customers with product questions, order status, tracking, "
            "return/cancellation policies, and general platform guidance. "
            "Always be concise, friendly, and professional. "
            "When a question is product-specific, suggest the customer message the seller directly."
        )

    async def generate_response(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> dict:
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in conversation_history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )
        reply = response.choices[0].message.content or ""
        return {
            "reply": reply,
            "suggested_action": self._detect_action(reply),
            "should_redirect_to_seller": "seller" in reply.lower(),
        }

    def _detect_action(self, reply: str) -> str:
        lower = reply.lower()
        if "cancel" in lower:
            return "cancel_order"
        if "return" in lower:
            return "return_request"
        if "track" in lower:
            return "track_order"
        return "general"
