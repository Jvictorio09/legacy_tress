"""AI preview generation for The Ethereal Boho style via OpenAI."""

from __future__ import annotations

import os
from io import BytesIO
from typing import BinaryIO

from django.conf import settings

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - optional in minimal deploys
    Image = None
    ImageOps = None

BOHO_PROMPT = (
    'Preserve the same person exactly: same face shape, facial features, skin tone, '
    'expression, glasses, accessories, pose, camera angle, clothing, and background. '
    'Change ONLY the hairstyle to long ethereal bohemian knotless braids, mid-back length, '
    'with soft curly boho ends and face-framing pieces inspired by "The Ethereal Boho". '
    'Keep everything else exactly the same. Photorealistic salon-quality result.'
)


class BohoPreviewError(Exception):
    """Raised when preview generation fails."""


def _api_key() -> str:
    return getattr(settings, 'OPENAI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')


def _image_model() -> str:
    return getattr(settings, 'OPENAI_IMAGE_MODEL', 'gpt-image-1')


def _upload_tuple(source: BinaryIO) -> tuple[str, BinaryIO, str]:
    content_type = getattr(source, 'content_type', None) or 'image/jpeg'
    filename = {
        'image/jpeg': 'selfie.jpg',
        'image/png': 'selfie.png',
        'image/webp': 'selfie.webp',
    }.get(content_type, 'selfie.jpg')
    source.seek(0)
    return filename, source, content_type


def _prepare_upload(source: BinaryIO) -> tuple[str, BytesIO | BinaryIO, str]:
    """Normalize the selfie for best face preservation (rotation, size, quality)."""
    if Image is None or ImageOps is None:
        return _upload_tuple(source)

    source.seek(0)
    try:
        image = ImageOps.exif_transpose(Image.open(source)).convert('RGB')
    except Exception as exc:
        raise BohoPreviewError('Could not read that photo. Please try another JPG or PNG.') from exc

    width, height = image.size
    max_dim = 1536
    if max(width, height) > max_dim:
        scale = max_dim / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=95)
    buffer.seek(0)
    return 'selfie.jpg', buffer, 'image/jpeg'


def _edit_image(client, upload):
    """Call OpenAI edit API; prefer high-fidelity when supported."""
    base = {
        'model': _image_model(),
        'image': upload,
        'prompt': BOHO_PROMPT,
        'size': '1024x1536',
    }
    fidelity = {
        'quality': 'high',
        'input_fidelity': 'high',
        'output_format': 'jpeg',
    }

    try:
        return client.images.edit(**base, **fidelity)
    except TypeError:
        # Older openai SDK (<2.x) does not accept fidelity/quality kwargs.
        return client.images.edit(**base)
    except Exception as exc:
        message = str(exc).lower()
        if any(token in message for token in ('input_fidelity', 'quality', 'output_format')):
            return client.images.edit(**base)
        raise


def _format_data_url(item) -> str:
    if getattr(item, 'b64_json', None):
        mime = 'image/jpeg' if getattr(item, 'output_format', None) == 'jpeg' else 'image/png'
        return f'data:{mime};base64,' + item.b64_json
    if getattr(item, 'url', None):
        return item.url
    raise BohoPreviewError('Unexpected response from the AI service.')


def generate_ethereal_boho_preview(source: BinaryIO) -> str:
    """Return a data URL or image URL for the generated preview."""
    api_key = _api_key()
    if not api_key:
        raise BohoPreviewError(
            'AI preview is not configured yet. Add OPENAI_API_KEY on the server.'
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise BohoPreviewError('OpenAI package is not installed on the server.') from exc

    upload = _prepare_upload(source)
    client = OpenAI(api_key=api_key)

    try:
        result = _edit_image(client, upload)
    except Exception as exc:
        detail = str(exc).strip()
        if settings.DEBUG and detail:
            raise BohoPreviewError(detail) from exc
        raise BohoPreviewError(
            'Could not generate your preview right now. Please try again in a moment.'
        ) from exc

    if not result.data:
        raise BohoPreviewError('No image was returned from the AI service.')

    return _format_data_url(result.data[0])
