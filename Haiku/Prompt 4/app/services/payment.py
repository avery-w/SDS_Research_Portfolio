import stripe
from app.config import get_settings

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY

def process_payment(amount: float, payment_method_id: str) -> dict:
    """
    Process payment via Stripe.
    ponytail: test mode with mock responses until real Stripe integration
    """

    try:
        if stripe.api_key.startswith("sk_test"):
            return {
                "success": True,
                "payment_id": f"pi_test_{payment_method_id}_{int(amount*100)}",
                "amount": amount,
                "status": "succeeded"
            }

        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd",
            payment_method=payment_method_id,
            confirm=True
        )

        if payment_intent.status == "succeeded":
            return {
                "success": True,
                "payment_id": payment_intent.id,
                "amount": amount,
                "status": payment_intent.status
            }
        else:
            return {
                "success": False,
                "error": f"Payment status: {payment_intent.status}"
            }
    except stripe.error.CardError as e:
        return {
            "success": False,
            "error": f"Card error: {e.user_message}"
        }
    except stripe.error.RateLimitError:
        return {
            "success": False,
            "error": "Rate limited by Stripe"
        }
    except stripe.error.InvalidRequestError as e:
        return {
            "success": False,
            "error": f"Invalid request: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Payment processing error: {str(e)}"
        }

def create_payment_intent(amount: float) -> dict:
    """Create a payment intent for frontend"""
    try:
        if stripe.api_key.startswith("sk_test"):
            return {
                "client_secret": f"pi_test_{int(amount*100)}_secret",
                "id": f"pi_test_{int(amount*100)}"
            }

        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd"
        )
        return {
            "client_secret": intent.client_secret,
            "id": intent.id
        }
    except Exception as e:
        return {"error": str(e)}
