from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from app.core.config import settings

class AIService:
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model="gpt-4o"
        )
        self.system_prompt = (
            "You are a helpful marketplace assistant. If a user asks specific questions "
            "about a product's condition, custom orders, or shipping specifics, "
            "politely direct them to message the seller directly using the 'Contact Seller' button."
        )

    async def get_chat_response(self, user_message: str, product_metadata: str = None) -> str:
        messages = [SystemMessage(content=self.system_prompt)]
        
        if product_metadata:
            messages.append(SystemMessage(content=f"Context about the current product: {product_metadata}"))
            
        messages.append(HumanMessage(content=user_message))
        
        response = self.llm.invoke(messages)
        return response.content
