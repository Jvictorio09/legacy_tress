from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .boho_ai import BohoPreviewError, generate_ethereal_boho_preview

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


class BohoTryOnView(TemplateView):
    template_name = 'boho_try_on.html'


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

        try:
            image_url = generate_ethereal_boho_preview(photo)
        except BohoPreviewError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=503)
        except Exception:
            return JsonResponse(
                {'ok': False, 'error': 'Something went wrong generating your preview. Please try again.'},
                status=500,
            )

        return JsonResponse({'ok': True, 'image_url': image_url})
