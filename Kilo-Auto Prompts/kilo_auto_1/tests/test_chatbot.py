"""Tests for chatbot."""
from __future__ import annotations

import pytest

from app.chatbot import chatbot_respond


class TestChatbotRulesEngine:
    @pytest.mark.asyncio
    async def test_greeting_response(self):
        result = await chatbot_respond("Hello there!")
        assert "response" in result
        assert result["intent"] == "greeting"

    @pytest.mark.asyncio
    async def test_order_status_intent(self):
        result = await chatbot_respond("Where is my order?")
        assert result["intent"] == "order_status"

    @pytest.mark.asyncio
    async def test_return_intent(self):
        result = await chatbot_respond("I want to return an item")
        assert result["intent"] == "return_policy"

    @pytest.mark.asyncio
    async def test_shipping_intent(self):
        result = await chatbot_respond("What are your shipping options?")
        assert result["intent"] == "shipping_info"

    @pytest.mark.asyncio
    async def test_contact_seller_intent(self):
        result = await chatbot_respond("I want to contact a seller")
        assert result["intent"] == "contact_seller"

    @pytest.mark.asyncio
    async def test_account_intent(self):
        result = await chatbot_respond("How do I reset my password?")
        assert result["intent"] == "account_help"

    @pytest.mark.asyncio
    async def test_payment_intent(self):
        result = await chatbot_respond("What payment methods do you accept?")
        assert result["intent"] == "payment_methods"

    @pytest.mark.asyncio
    async def test_farewell_intent(self):
        result = await chatbot_respond("Thanks for your help!")
        assert result["intent"] == "farewell"

    @pytest.mark.asyncio
    async def test_fallback_for_unknown(self):
        result = await chatbot_respond("Blah blah quantum computing foo bar")
        assert "response" in result
        assert result["intent"] is None or result["intent"] == "default"

    @pytest.mark.asyncio
    async def test_product_suggestion(self):
        result = await chatbot_respond("Is this product available in blue?", product_id=123)
        assert "response" in result
        # Should suggest contacting seller for product-specific questions
        assert result["suggest_seller"] is True or result["product_id"] == 123

    @pytest.mark.asyncio
    async def test_order_suggestion(self):
        result = await chatbot_respond("Where is my order?", order_id=456)
        assert "response" in result
        assert result["order_id"] == 456

    @pytest.mark.asyncio
    async def test_session_generation(self):
        result = await chatbot_respond("Hello")
        assert result["session_id"] is not None
        assert len(result["session_id"]) > 0

    @pytest.mark.asyncio
    async def test_returns_session_id(self):
        result1 = await chatbot_respond("Hello")
        result2 = await chatbot_respond("Hello", session_id=result1["session_id"])
        assert result2["session_id"] == result1["session_id"]


class TestChatbotOpenAI:
    @pytest.mark.asyncio
    async def test_fallback_when_no_api_key(self):
        """When no OpenAI API key is set, rules engine should handle it."""
        import os
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            result = await chatbot_respond("Hello")
            assert "response" in result
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original
