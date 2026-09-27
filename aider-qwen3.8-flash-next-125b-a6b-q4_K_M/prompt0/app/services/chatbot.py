import openai
from flask import current_app

class ChatbotService:
    """
    AI chatbot that assists customers and encourages them to
    message sellers directly for product/order questions.
    """

    SYSTEM_PROMPT = (
        "You are a friendly, helpful AI assistant for an e-commerce marketplace. "
        "Your role is to help customers with general questions about the platform, "
        "order status, shipping, returns, and account management. "
        "IMPORTANT: If a customer asks a specific question about a product's details, "
        "availability, customization, or a specific order's status, you MUST encourage them "
        "to message the seller directly through the in-app messaging system. "
        "Say something like: 'For that specific question, I'd recommend messaging the seller "
        "directly through the chat feature on their store page — they'll be able to give you "
        "the most accurate and up-to-date answer!' "
        "Keep responses concise, friendly, and under 150 words."
    )

    @classmethod
    def get_response(cls, user_message: str, conversation_history: list = None) -> str:
        """
        conversation_history: list of dicts [{"role": "user"/"assistant", "content": "..."}]
        Returns the assistant's reply string.
        """
        client = openai.OpenAI(api_key=current_app.config["OPENAI_API_KEY"])

        messages = [{"role": "system", "content": cls.SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except openai.APIError as e:
            current_app.logger.error(f"OpenAI error: {e}")
            return ("I'm sorry, I'm having trouble connecting right now. "
                    "Please try again shortly, or message a seller directly "
                    "through the in-app chat for immediate help!")
