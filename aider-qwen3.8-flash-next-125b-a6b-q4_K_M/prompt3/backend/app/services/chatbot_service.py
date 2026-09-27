import uuid
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_community.document_loaders import StringLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config import get_settings
from app.schemas.chatbot import ChatbotResponse

settings = get_settings()

llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0.3)

SYSTEM_PROMPT = """You are a helpful marketplace assistant. Answer the user's question using ONLY the retrieved context.
If the answer is not in the context, say: "I'm not sure about that. Would you like me to connect you with the seller directly?"
and set suggest_seller_message to true."""


async def ask_chatbot(question: str, context_docs: list[Document] | None = None) -> ChatbotResponse:
    from langchain_core.messages import SystemMessage, HumanMessage

    context_text = "\n\n".join([d.page_content for d in (context_docs or [])])
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context_text}\n\nQuestion: {question}"),
    ]
    response = await llm.ainvoke(messages)
    answer = response.content
    suggest = "seller" in answer.lower() and "connect" in answer.lower()
    return ChatbotResponse(answer=answer, suggest_seller_message=suggest)
