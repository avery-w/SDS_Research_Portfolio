import os
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from fastapi import HTTPException

def get_ai_response(user_query: str, product_context: str = None):
    """
    Handles AI Chatbot logic using LangChain and OpenAI.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "AI service is currently unavailable. Please contact support."

    try:
        llm = ChatOpenAI(model="gpt-4o", openai_api_key=api_key)
        
        system_prompt = (
            "You are a helpful e-commerce assistant. Your goal is to help customers find products. "
            "If a customer asks a specific question about a product's condition, shipping, "
            "or custom requests, politely encourage them to message the seller directly "
            "using the 'Message Seller' button for the most accurate information."
        )
        
        messages = [SystemMessage(content=system_prompt)]
        
        if product_context:
            messages.append(SystemMessage(content=f"Current Product Context: {product_context}"))
            
        messages.append(HumanMessage(content=user_query))
        
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Chatbot error: {str(e)}")
