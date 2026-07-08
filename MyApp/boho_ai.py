"""AI braid preview generation via OpenAI image edit."""

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

_BASE_PRESERVE = (
    'Preserve the same person exactly: same face shape, facial features, skin tone, '
    'expression, glasses, accessories, pose, camera angle, clothing, and background. '
    'Change ONLY the hairstyle to {style}. '
    'Keep everything else exactly the same. Photorealistic salon-quality result.'
)

_IMG = {
    'knotless': 'https://images.leadconnectorhq.com/image/f_webp/q_80/r_600/u_https://assets.cdn.filesafe.space/PdsP45Yo0hioveq4oKF8/media/69272023c3c18212c2317c66.jpg',
    'boho': 'https://images.leadconnectorhq.com/image/f_webp/q_80/r_600/u_https://assets.cdn.filesafe.space/PdsP45Yo0hioveq4oKF8/media/69150d324a60b5912d8e4bb0.jpg',
    'french': 'https://images.leadconnectorhq.com/image/f_webp/q_80/r_600/u_https://assets.cdn.filesafe.space/PdsP45Yo0hioveq4oKF8/media/691c9d2a6a5d3b1bed979aa0.jpg',
    'petite': 'https://images.leadconnectorhq.com/image/f_webp/q_80/r_600/u_https://assets.cdn.filesafe.space/PdsP45Yo0hioveq4oKF8/media/6915e15744003e7298632783.jpg',
    'detail': 'https://images.leadconnectorhq.com/image/f_webp/q_80/r_600/u_https://assets.cdn.filesafe.space/PdsP45Yo0hioveq4oKF8/media/69385c4c35652b8ef108610d.png',
}

# All braid styles from the live Fresha menu — for AI preview testing.
BRAID_STYLE_CATALOG: list[dict] = [
    {
        'id': '22618040',
        'name': 'The Signature Knotless (SMEDIUM)',
        'category': 'Knotless',
        'time': '5 hr',
        'price': 275,
        'image': _IMG['knotless'],
        'hair': 'sleek smedium knotless box braids, shoulder to mid-back length, neat parts, natural density',
    },
    {
        'id': '22618100',
        'name': 'The Classic Knotless (MEDIUM)',
        'category': 'Knotless',
        'time': '4 hr',
        'price': 255,
        'image': _IMG['detail'],
        'hair': 'classic medium knotless braids, shoulder length, clean scalp parts, polished salon finish',
    },
    {
        'id': '22694942',
        'name': 'The Ethereal Boho (MID-BACK)',
        'category': 'Boho',
        'time': '6 hr',
        'price': 400,
        'image': _IMG['boho'],
        'hair': 'long ethereal bohemian knotless braids, mid-back length, soft curly boho ends and face-framing pieces',
    },
    {
        'id': '22618012',
        'name': 'The Delicate Knotless (SMALL)',
        'category': 'Knotless',
        'time': '6 hr',
        'price': 300,
        'image': _IMG['french'],
        'hair': 'small delicate knotless braids, fine parts, mid-back length, lightweight and elegant',
    },
    {
        'id': '24054136',
        'name': 'Small Bora-Bora Bohemian',
        'category': 'Bora-Bora',
        'time': '7 hr',
        'price': 700,
        'image': _IMG['boho'],
        'hair': 'small bohemian knotless braids with luxe curly boho pieces throughout, waist-length, island-inspired fullness',
    },
    {
        'id': '24054131',
        'name': 'Smedium Bora-Bora Bohemian',
        'category': 'Bora-Bora',
        'time': '6 hr',
        'price': 600,
        'image': _IMG['boho'],
        'hair': 'smedium bohemian knotless braids with flowing curly boho accents, mid-back to waist length, voluminous',
    },
    {
        'id': '26354770',
        'name': 'The Petite Knotless (X-SMALL W/HUMAN HAIR)',
        'category': 'Knotless',
        'time': '6 hr',
        'price': 700,
        'image': _IMG['petite'],
        'hair': 'extra-small petite knotless braids with human-hair blend, neat micro parts, mid-back length, child-friendly scale',
    },
    {
        'id': '26512318',
        'name': 'The Petite Knotless (X-SMALL)',
        'category': 'Knotless',
        'time': '5 hr',
        'price': 500,
        'image': _IMG['petite'],
        'hair': 'extra-small petite knotless braids, fine neat parts, mid-back length, lightweight protective style',
    },
    {
        'id': '22694961',
        'name': 'The Romantic Boho (WAIST-LENGTH)',
        'category': 'Boho',
        'time': '7 hr',
        'price': 525,
        'image': _IMG['boho'],
        'hair': 'romantic waist-length bohemian knotless braids with soft curly ends and wispy face-framing tendrils',
    },
    {
        'id': '22824921',
        'name': 'Afro Twist W/ Human Hair',
        'category': 'Twists',
        'time': '6 hr',
        'price': 500,
        'image': _IMG['detail'],
        'hair': 'fluffy afro two-strand twists with human hair blend, mid-back length, natural texture, springy ends',
    },
    {
        'id': '22696365',
        'name': 'Afro Kinky Twist',
        'category': 'Twists',
        'time': '5 hr',
        'price': 350,
        'image': _IMG['detail'],
        'hair': 'afro kinky two-strand twists, shoulder to mid-back, textured springy coils, full-bodied protective style',
    },
    {
        'id': '23868539',
        'name': 'Marley Twist',
        'category': 'Twists',
        'time': '5 hr',
        'price': 300,
        'image': _IMG['detail'],
        'hair': 'marley hair two-strand twists, shoulder to mid-back, rope-like texture, neat parts',
    },
    {
        'id': '22697168',
        'name': 'Boho Fulani Braids',
        'category': 'Fulani',
        'time': '5 hr',
        'price': 450,
        'image': _IMG['knotless'],
        'hair': 'fulani-inspired braids with center braid, decorative beads or cuffs, curly boho pieces at ends, mid-back length',
    },
    {
        'id': '22697157',
        'name': 'Knotless Fulani Braids',
        'category': 'Fulani',
        'time': '4 hr',
        'price': 300,
        'image': _IMG['knotless'],
        'hair': 'knotless fulani braids with tribal-inspired parts, center cornrow detail, mid-back length, clean scalp',
    },
    {
        'id': '24664196',
        'name': 'Boho Passion Twist',
        'category': 'Passion Twist',
        'time': '5 hr',
        'price': 450,
        'image': _IMG['boho'],
        'hair': 'passion twists with boho curly pieces mixed in, mid-back length, soft bohemian texture',
    },
    {
        'id': '22696431',
        'name': 'Passion Twist',
        'category': 'Passion Twist',
        'time': '4 hr',
        'price': 300,
        'image': _IMG['boho'],
        'hair': 'silky passion twists, shoulder to mid-back, springy curled ends, neat parts',
    },
    {
        'id': '24655148',
        'name': 'Boho Knotless Sew-In',
        'category': 'Fusion',
        'time': '4 hr',
        'price': 350,
        'image': _IMG['detail'],
        'hair': 'knotless braids blended with sew-in boho curly pieces, mid-back length, seamless fusion look',
    },
    {
        'id': '23613184',
        'name': 'Fulani Sew-In',
        'category': 'Fusion',
        'time': '5 hr',
        'price': 400,
        'image': _IMG['detail'],
        'hair': 'fulani braids with sew-in curly accent hair, decorative tribal parts, mid-back length',
    },
    {
        'id': '22694901',
        'name': 'Boho Bob (FULL)',
        'category': 'Boho Bob',
        'time': '5 hr',
        'price': 525,
        'image': _IMG['boho'],
        'hair': 'full boho bob braids, chin to collarbone length, curly boho ends, face-framing volume',
    },
    {
        'id': '22694876',
        'name': 'Boho Bob (MID)',
        'category': 'Boho Bob',
        'time': '4 hr',
        'price': 450,
        'image': _IMG['boho'],
        'hair': 'mid-length boho bob braids, jaw-length with soft curly boho pieces, chic and full',
    },
    {
        'id': '26146214',
        'name': 'Boho French Curls',
        'category': 'French',
        'time': '5 hr',
        'price': 400,
        'image': _IMG['french'],
        'hair': 'knotless braids with luxurious french curl ends, mid-back length, bouncy spiral curls at tips',
    },
    {
        'id': '22618370',
        'name': 'Knotless French Braids',
        'category': 'French',
        'time': '4 hr',
        'price': 315,
        'image': _IMG['french'],
        'hair': 'knotless braids with classic french curl ends, shoulder to mid-back, defined spiral tips',
    },
    {
        'id': '27851770',
        'name': 'Feather Crochet',
        'category': 'Crochet',
        'time': '3 hr',
        'price': 300,
        'image': _IMG['detail'],
        'hair': 'feather-light crochet braids, fluffy textured curls, shoulder to mid-back, soft volume',
    },
    {
        'id': '25995983',
        'name': 'Small Miracle Knotless Boho Braids',
        'category': 'Gray',
        'time': '6 hr',
        'price': 355,
        'image': _IMG['knotless'],
        'hair': 'small knotless boho braids in salt-and-pepper gray blend, mid-back length, curly boho ends',
    },
    {
        'id': '25995971',
        'name': 'Miracle Knotless Braids (S-MEDIUM)',
        'category': 'Gray',
        'time': '5 hr',
        'price': 300,
        'image': _IMG['knotless'],
        'hair': 'smedium knotless braids in elegant silver-gray tones, mid-back length, polished mature look',
    },
    {
        'id': '25995906',
        'name': 'Medium Miracle Boho Braids',
        'category': 'Gray',
        'time': '5 hr',
        'price': 255,
        'image': _IMG['boho'],
        'hair': 'medium boho braids in blended gray tones, mid-back length, soft curly boho ends',
    },
    {
        'id': '25552085',
        'name': "Queen's Shadow Gray",
        'category': 'Gray',
        'time': '6 hr',
        'price': 400,
        'image': _IMG['detail'],
        'hair': 'dramatic shadow-root gray knotless braids, deep charcoal roots fading to silver-gray, mid-back length',
    },
]

BRAID_STYLES_BY_ID = {item['id']: item for item in BRAID_STYLE_CATALOG}

DEFAULT_STYLE_ID = '22694942'


class BohoPreviewError(Exception):
    """Raised when preview generation fails."""


def get_braid_style_catalog() -> list[dict]:
    """Return braid styles safe for JSON/API (no internal prompt fields)."""
    return [
        {
            'id': item['id'],
            'name': item['name'],
            'category': item['category'],
            'time': item['time'],
            'price': item['price'],
            'image': item['image'],
        }
        for item in BRAID_STYLE_CATALOG
    ]


def get_braid_categories() -> list[str]:
    seen: list[str] = []
    for item in BRAID_STYLE_CATALOG:
        cat = item['category']
        if cat not in seen:
            seen.append(cat)
    return seen


def _prompt_for_style(style_id: str) -> str:
    style = BRAID_STYLES_BY_ID.get(style_id) or BRAID_STYLES_BY_ID[DEFAULT_STYLE_ID]
    return _BASE_PRESERVE.format(style=style['hair'])


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


def _edit_image(client, upload, prompt: str):
    """Call OpenAI edit API; prefer high-fidelity when supported."""
    base = {
        'model': _image_model(),
        'image': upload,
        'prompt': prompt,
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


def generate_braid_preview(source: BinaryIO, style_id: str | None = None) -> tuple[str, dict]:
    """Return image URL/data URL and the resolved style metadata."""
    resolved_id = style_id if style_id in BRAID_STYLES_BY_ID else DEFAULT_STYLE_ID
    style = BRAID_STYLES_BY_ID[resolved_id]
    prompt = _prompt_for_style(resolved_id)

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
        result = _edit_image(client, upload, prompt)
    except Exception as exc:
        detail = str(exc).strip()
        if settings.DEBUG and detail:
            raise BohoPreviewError(detail) from exc
        raise BohoPreviewError(
            'Could not generate your preview right now. Please try again in a moment.'
        ) from exc

    if not result.data:
        raise BohoPreviewError('No image was returned from the AI service.')

    image_url = _format_data_url(result.data[0])
    meta = {
        'id': style['id'],
        'name': style['name'],
        'category': style['category'],
    }
    return image_url, meta


def generate_ethereal_boho_preview(source: BinaryIO) -> str:
    """Backward-compatible helper for the original Ethereal Boho-only flow."""
    image_url, _meta = generate_braid_preview(source, DEFAULT_STYLE_ID)
    return image_url
