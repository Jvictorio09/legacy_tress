import json

from django.http import JsonResponse
from django.views import View
from django.views.csrf import csrf_failure as django_csrf_failure
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .ai_concierge import ConciergeError, create_chat_reply, create_realtime_session
from .boho_ai import BohoPreviewError, generate_braid_preview, get_braid_style_catalog

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}


class IndexView(TemplateView):
    template_name = 'index.html'


class PoliciesView(TemplateView):
    template_name = 'policies.html'


class OrchestraView(TemplateView):
    template_name = 'orchestra.html'


class PlanView(TemplateView):
    template_name = 'plan.html'


class TryOnView(TemplateView):
    template_name = 'try_on.html'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class BohoTryOnView(TemplateView):
    template_name = 'boho_try_on.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['braid_styles'] = get_braid_style_catalog()
        return context


def csrf_failure(request, reason=''):
    """Return JSON for API calls so the browser never tries to parse an HTML 403."""
    content_type = request.content_type or ''
    wants_json = (
        request.path.startswith('/api/')
        or 'application/json' in request.headers.get('Accept', '')
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or content_type == 'application/json'
        or content_type.startswith('multipart/')
    )
    if wants_json:
        return JsonResponse(
            {'ok': False, 'error': 'Your session expired. Refresh the page and try again.'},
            status=403,
        )
    return django_csrf_failure(request, reason)


@method_decorator(csrf_protect, name='dispatch')
class BohoGenerateView(View):
    """Accept a selfie and return an AI Ethereal Boho preview URL."""

    def post(self, request):
        photo = request.FILES.get('photo')
        if not photo:
            return JsonResponse({'ok': False, 'error': 'Please upload or capture a photo first.'}, status=400)

        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            return JsonResponse({'ok': False, 'error': 'Please use a JPG, PNG, or WebP photo.'}, status=400)

        if photo.size > MAX_UPLOAD_BYTES:
            return JsonResponse({'ok': False, 'error': 'Photo is too large. Please use an image under 10 MB.'}, status=400)

        style_id = (request.POST.get('style') or '').strip()

        try:
            image_url, style = generate_braid_preview(photo, style_id or None)
        except BohoPreviewError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=503)
        except Exception:
            return JsonResponse(
                {'ok': False, 'error': 'Something went wrong generating your preview. Please try again.'},
                status=500,
            )

        return JsonResponse({'ok': True, 'image_url': image_url, 'style': style})


@method_decorator(csrf_protect, name='dispatch')
class AIConciergeChatView(View):
    """Text chat with the LegacyTress AI Hair Concierge."""

    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({'ok': False, 'error': 'Invalid request.'}, status=400)

        try:
            reply = create_chat_reply(body.get('messages'))
        except ConciergeError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=503)
        except Exception:
            return JsonResponse(
                {'ok': False, 'error': 'Something went wrong. Please try again.'},
                status=500,
            )

        return JsonResponse({'ok': True, 'reply': reply})


@method_decorator(csrf_protect, name='dispatch')
class AIConciergeRealtimeSessionView(View):
    """Mint a short-lived ephemeral key for a browser WebRTC voice call."""

    def post(self, request):
        try:
            session = create_realtime_session()
        except ConciergeError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=503)
        except Exception:
            return JsonResponse(
                {'ok': False, 'error': 'Could not start a voice session. Please try again.'},
                status=500,
            )

        return JsonResponse({'ok': True, **session})
