import os, stripe
stripe.api_key = os.getenv('STRIPE_API_KEY','')

def create_payment_intent_cents(order_id, amount_cents, currency='usd'):
    if not stripe.api_key: return {'mock': True, 'client_secret': f'mock_{order_id}'}
    intent = stripe.PaymentIntent.create(amount=amount_cents, currency=currency, metadata={'order_id': str(order_id)})
    return {'client_secret': intent.client_secret}
