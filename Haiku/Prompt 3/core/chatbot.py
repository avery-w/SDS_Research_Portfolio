from .models import ChatbotLog, Product
import json

class MarketplaceChatbot:
    def __init__(self):
        self.context_products = []

    def process_message(self, user_message, user=None, product=None):
        lower_msg = user_message.lower()

        if any(word in lower_msg for word in ['price', 'cost', 'how much']):
            response = self._handle_pricing_query(product)
        elif any(word in lower_msg for word in ['ship', 'delivery', 'arrive', 'tracking']):
            response = self._handle_shipping_query()
        elif any(word in lower_msg for word in ['return', 'refund', 'exchange']):
            response = self._handle_return_query()
        elif any(word in lower_msg for word in ['payment', 'card', 'stripe', 'pay']):
            response = self._handle_payment_query()
        elif any(word in lower_msg for word in ['product', 'item', 'about', 'describe']):
            response = self._handle_product_query(product)
        elif any(word in lower_msg for word in ['contact', 'seller', 'question', 'seller']):
            response = self._suggest_seller_contact(product)
        else:
            response = self._default_response()

        if user:
            ChatbotLog.objects.create(
                user=user,
                user_message=user_message,
                bot_response=response,
                product=product,
            )

        return response

    def _handle_pricing_query(self, product):
        if product:
            return f"This product is priced at ${product.price}. Would you like to add it to your cart or have more questions about it?"
        return "I can help you with pricing information. Please select a product or ask your question in more detail."

    def _handle_shipping_query(self):
        return "We offer shipping to most locations in the US. Delivery typically takes 5-7 business days. Shipping costs are calculated at checkout based on your location and package weight."

    def _handle_return_query(self):
        return "We offer returns within 30 days of purchase. Please visit your order history to request a return. You'll receive a prepaid shipping label and full refund once we receive and inspect the item."

    def _handle_payment_query(self):
        return "We accept all major credit cards, debit cards, and PayPal through Stripe. Your payment information is encrypted and secure."

    def _handle_product_query(self, product):
        if product:
            specs = []
            if product.weight_kg:
                specs.append(f"Weight: {product.weight_kg}kg")
            if product.dimensions_length:
                specs.append(f"Dimensions: {product.dimensions_length}x{product.dimensions_width}x{product.dimensions_height}cm")

            spec_text = ", ".join(specs) if specs else "No detailed specs listed"
            return f"{product.name}: {product.description}\n{spec_text}\nWould you like to message the seller for more details?"
        return "Please select a product to learn more about it."

    def _suggest_seller_contact(self, product):
        if product:
            return f"Great question! I recommend messaging the seller directly about this product. They can provide expert advice and answer any specific questions. Would you like me to help you start a conversation?"
        return "You can message any seller to ask questions about their products. Browse a product and click 'Contact Seller' to start a conversation."

    def _default_response(self):
        return "I'm here to help! You can ask me about products, pricing, shipping, returns, or payment. For more complex questions, I can connect you with the seller. What would you like to know?"
