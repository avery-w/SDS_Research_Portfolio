import openai
from flask import current_app
from app.models import Product, Store, User, Order


class ChatbotService:
    def __init__(self):
        self.api_key = current_app.config.get('OPENAI_API_KEY', '')
        self.model = current_app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.use_ai = bool(self.api_key)

    def get_response(self, user_message, user):
        lower_msg = user_message.lower()

        product_match = self._find_product_mention(user_message)
        if product_match and self._should_suggest_seller(lower_msg):
            return {
                'message': f'I found "{product_match.name}" from {product_match.store.name}. '
                           f'Would you like me to help you contact the seller directly? '
                           f'They can answer specific questions about this product.',
                'suggest_seller_contact': True,
                'seller_id': product_match.store.seller_id,
                'product_id': product_match.id
            }

        if any(word in lower_msg for word in ['shipping', 'delivery', 'how long', 'arrive']):
            return {
                'message': 'We offer several shipping options:\n'
                           '- UPS Ground: 5-7 business days\n'
                           '- UPS 3 Day Select: 3 business days\n'
                           '- UPS 2nd Day Air: 2 business days\n'
                           '- UPS Next Day Air: 1 business day\n'
                           '- Free shipping on orders over $75!\n\n'
                           'Orders ship from our Austin, TX facility.',
                'suggest_seller_contact': False
            }

        if any(word in lower_msg for word in ['return', 'refund', 'exchange']):
            return {
                'message': 'Our return policy allows returns within 30 days of delivery. '
                           'To initiate a return, go to your Orders page and click '
                           '"Request Return" on the delivered order. '
                           'Refunds are processed within 5-7 business days.',
                'suggest_seller_contact': False
            }

        if any(word in lower_msg for word in ['payment', 'pay', 'credit card', 'paypal']):
            return {
                'message': 'We accept the following payment methods:\n'
                           '- Credit Cards (Visa, Mastercard, Amex, Discover)\n'
                           '- Debit Cards\n'
                           '- PayPal\n\n'
                           'All transactions are secured with SSL encryption.',
                'suggest_seller_contact': False
            }

        if any(word in lower_msg for word in ['contact', 'message', 'seller', 'vendor']):
            return {
                'message': 'You can message sellers directly from any product page '
                           'or through the Messages section. Sellers typically respond '
                           'within 24 hours. Would you like to browse our sellers?',
                'suggest_seller_contact': False
            }

        if any(word in lower_msg for word in ['order', 'track', 'where']):
            if user.is_authenticated:
                recent_orders = Order.query.filter_by(
                    customer_id=user.id
                ).order_by(Order.created_at.desc()).limit(3).all()
                if recent_orders:
                    order_info = '\n'.join([
                        f'- {o.order_number}: {o.status}' for o in recent_orders
                    ])
                    return {
                        'message': f'Here are your recent orders:\n{order_info}\n\n'
                                   f'Visit your Orders page for full details and tracking info.',
                        'suggest_seller_contact': False
                    }
            return {
                'message': 'To track your order, please sign in and visit the Orders page. '
                           'You can also message the seller directly for updates.',
                'suggest_seller_contact': False
            }

        if any(word in lower_msg for word in ['hello', 'hi', 'hey', 'help']):
            return {
                'message': f'Hello! I\'m the LongCat Marketplace assistant. I can help you with:\n'
                           f'- Finding products and connecting with sellers\n'
                           f'- Shipping and delivery information\n'
                           f'- Returns and refunds\n'
                           f'- Payment methods\n'
                           f'- Order tracking\n\n'
                           f'How can I help you today?',
                'suggest_seller_contact': False
            }

        if self.use_ai:
            return self._get_ai_response(user_message, user)

        return {
            'message': 'I can help you with product questions, shipping info, returns, '
                       'and order tracking. For specific product questions, '
                       'I can connect you directly with the seller. '
                       'What would you like to know?',
            'suggest_seller_contact': False
        }

    def _find_product_mention(self, message):
        products = Product.query.filter_by(is_active=True).all()
        words = message.lower().split()

        best_match = None
        best_score = 0

        for product in products:
            name_words = product.name.lower().split()
            score = sum(1 for word in words if word in name_words and len(word) > 2)
            if score > best_score:
                best_score = score
                best_match = product

        return best_match if best_score >= 1 else None

    def _should_suggest_seller(self, message):
        seller_triggers = [
            'question about', 'more info', 'tell me about', 'details about',
            'is it', 'does it', 'what size', 'what color', 'available',
            'warranty', 'specification', 'compatible', 'difference'
        ]
        return any(trigger in message for trigger in seller_triggers)

    def _get_ai_response(self, user_message, user):
        try:
            openai.api_key = self.api_key

            system_prompt = (
                "You are a helpful customer service assistant for LongCat Marketplace, "
                "a multi-vendor e-commerce platform. Be concise and friendly. "
                "If customers ask about specific products, encourage them to message "
                "the seller directly for detailed product questions. "
                "Key info: Free shipping over $75, 30-day returns, ships from Austin TX. "
                "Keep responses under 3 sentences unless more detail is needed."
            )

            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=200,
                temperature=0.7
            )

            return {
                'message': response.choices[0].message.content,
                'suggest_seller_contact': False
            }
        except Exception as e:
            current_app.logger.error(f'OpenAI API error: {e}')
            return {
                'message': 'I apologize, but I\'m having trouble connecting right now. '
                           'Please try again or contact our support team for assistance.',
                'suggest_seller_contact': False
            }
