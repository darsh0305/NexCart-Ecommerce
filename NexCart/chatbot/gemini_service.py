import logging

from django.conf import settings
from google import genai

from .nexcart_knowledge import NEXCART_KNOWLEDGE

logger = logging.getLogger(__name__)


class GeminiUnavailableError(Exception):
    """Raised when the Gemini API is not configured or fails."""
    pass


def api_available():
    """Check whether the Gemini API key is configured (lightweight, no API call)."""
    return bool(settings.GEMINI_API_KEY)


def get_gemini_response(user_message, nexcart_context=''):
    """
    Send the user message + live NexCart context to Gemini and return
    a natural-language response.

    Raises GeminiUnavailableError if the API key is missing or the call fails.
    """
    if not settings.GEMINI_API_KEY:
        logger.error('GEMINI_API_KEY is not set in environment / settings.')
        raise GeminiUnavailableError(
            'Gemini API key is not configured. '
            'Add GEMINI_API_KEY to your .env file.'
        )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = f"""
{NEXCART_KNOWLEDGE}

========================
LIVE NEXCART DATA
========================

{nexcart_context}

========================
CUSTOMER QUESTION
========================

{user_message}

========================
IMPORTANT RULES
========================

1. You are NexCart AI, the official AI shopping assistant for the NexCart e-commerce platform.
2. Use ONLY the NexCart information provided in the context above.
3. Do not invent products, prices, stock, categories, orders, ratings, delivery statuses, or payment information.
4. If the provided context does not contain the requested information, say that the information is unavailable instead of guessing.
5. For customer-specific information, only use information belonging to the authenticated customer shown in the context.
6. Be concise, helpful and professional.
7. When discussing products, use the actual product information supplied by NexCart.
8. When discussing orders, use only the authenticated customer's order information.
9. Never expose API keys, passwords, card numbers, CVV, OTP, or other sensitive data.
10. If the customer is not logged in and asks for personal data (orders, cart, etc.), ask them to log in first.
11. Keep responses concise — avoid walls of text.
"""

        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=prompt,
        )

        return response.text

    except GeminiUnavailableError:
        raise

    except Exception as exc:
        logger.exception('Gemini API call failed: %s', exc)
        raise GeminiUnavailableError(
            'Gemini API call failed. Check server logs for details.'
        ) from exc
