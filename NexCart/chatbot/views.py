import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .context_builder import build_nexcart_context
from .gemini_service import GeminiUnavailableError, api_available, get_gemini_response

logger = logging.getLogger(__name__)


@require_GET
def health_check(request):
    """
    Lightweight endpoint for the frontend to check if the AI is configured.
    Does not make an actual API call to save latency and costs.
    """
    if api_available():
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'unavailable'})


@require_POST
def chat(request):
    """
    Main chatbot interaction endpoint.
    Retrieves live NexCart context and queries Gemini.
    """
    try:
        data = json.loads(request.body)
        message = (data.get('message') or '').strip()

        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a message.'
            }, status=400)

        if len(message) > 2000:
            return JsonResponse({
                'success': False,
                'error': 'Message is too long.'
            }, status=400)

        # Build live NexCart context from the database based on detected intent
        nexcart_context = build_nexcart_context(
            request.user,
            message,
        )

        # Ask Gemini
        response = get_gemini_response(
            message,
            nexcart_context,
        )

        return JsonResponse({
            'success': True,
            'response': response,
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request.'
        }, status=400)

    except GeminiUnavailableError as error:
        # Expected error when API is down or key is missing
        logger.warning('NexCart AI Unavailable: %s', error)
        return JsonResponse({
            'success': False,
            'error': 'NexCart AI is temporarily unavailable.',
        }, status=503)

    except Exception as error:
        # Unexpected server errors
        logger.exception('NexCart AI Error: %s', error)
        return JsonResponse({
            'success': False,
            'error': 'NexCart AI encountered an unexpected error.',
        }, status=500)
