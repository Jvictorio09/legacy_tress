"""LegacyTress AI Hair Concierge.

Provides two server-side helpers that reuse the existing OPENAI_API_KEY:

- ``create_chat_reply``          -> text chat via Chat Completions.
- ``create_realtime_session``    -> mints a short-lived ephemeral key for
  browser WebRTC voice calls (OpenAI Realtime API, GA interface). The long
  lived API key never leaves the server.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from django.conf import settings

REALTIME_CLIENT_SECRETS_URL = 'https://api.openai.com/v1/realtime/client_secrets'

# Chat + realtime models (overridable via settings / env).
DEFAULT_CHAT_MODEL = 'gpt-4o-mini'
DEFAULT_REALTIME_MODEL = 'gpt-realtime'
# Warm female voice for the concierge. Valid GA realtime voices:
# alloy, ash, ballad, coral, echo, sage, shimmer, verse, marin, cedar.
DEFAULT_VOICE = 'coral'

MAX_MESSAGES = 20
MAX_CHARS_PER_MESSAGE = 2000

SYSTEM_PROMPT = (
    "You are the LegacyTress AI Hair Concierge, the warm and knowledgeable virtual "
    "host for LegacyTress, a luxury wellness braiding salon in Margate, Florida "
    "(7644 Margate Boulevard). You help guests with braiding services, healthy-hair "
    "guidance, and booking.\n\n"
    "About LegacyTress:\n"
    "- Signature collections: knotless braids, boho braids, Fulani, passion twists, "
    "fusion sew-ins, French curl, crochet, and gray/silver collections.\n"
    "- Also offered: braid refresh, wash services, touch-ups, take-downs, and scalp "
    "consultations. Petite Knotless is ideal for children and smaller heads.\n"
    "- Retail: LegacyTress Oil and steam + tea-rinse treatments for healthy hair.\n"
    "- Booking is done on Fresha. Guests can book any service instantly there.\n"
    "- Two AI experiences on the site: the Virtual Color Studio (/try-on/) to preview "
    "hair colors, and Ethereal Boho AI (/try-on/ethereal-boho/) to preview braid styles "
    "on a selfie.\n\n"
    "How to respond:\n"
    "- Be warm, concise, and elegant. Keep replies to a few short sentences.\n"
    "- Guide guests toward booking on Fresha or trying the AI previews when relevant.\n"
    "- Encourage a scalp consultation for personalised advice or complex needs.\n"
    "- Prices and timing are confirmed on Fresha at booking and vary with length and "
    "density, so avoid quoting exact prices; point guests to the live menu instead.\n"
    "- Never make medical or dermatological claims. For scalp concerns, recommend an "
    "in-person consultation.\n"
    "- Stay on topic: LegacyTress services, hair care, and booking. Politely redirect "
    "off-topic questions back to how you can help with their hair."
)

# Text-chat only: a booking button is rendered client-side wherever the marker appears.
CHAT_SYSTEM_PROMPT = SYSTEM_PROMPT + (
    "\n\nBooking button (text chat only):\n"
    "- Whenever a guest asks about booking, appointments, availability, prices, a "
    "specific service, or seems ready to reserve, warmly invite them to book and place "
    "the marker [[BOOK]] on its own line at the end of that reply. A styled 'Book on "
    "Fresha' button is inserted automatically wherever the marker appears.\n"
    "- Never write out a booking link or URL yourself; use the [[BOOK]] marker instead, "
    "and only include it when booking is genuinely relevant."
)


class ConciergeError(Exception):
    """Raised when the concierge cannot fulfil a request."""


def _api_key() -> str:
    return getattr(settings, 'OPENAI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')


def _chat_model() -> str:
    return getattr(settings, 'OPENAI_CHAT_MODEL', DEFAULT_CHAT_MODEL)


def _realtime_model() -> str:
    return getattr(settings, 'OPENAI_REALTIME_MODEL', DEFAULT_REALTIME_MODEL)


def _voice() -> str:
    return getattr(settings, 'OPENAI_CONCIERGE_VOICE', DEFAULT_VOICE)


def _clean_messages(raw) -> list[dict]:
    """Validate and trim the client-provided chat history."""
    if not isinstance(raw, list):
        raise ConciergeError('Invalid message format.')

    cleaned: list[dict] = []
    for item in raw[-MAX_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get('role')
        content = item.get('content')
        if role not in ('user', 'assistant') or not isinstance(content, str):
            continue
        content = content.strip()[:MAX_CHARS_PER_MESSAGE]
        if content:
            cleaned.append({'role': role, 'content': content})

    if not cleaned or cleaned[-1]['role'] != 'user':
        raise ConciergeError('Please send a message to continue.')
    return cleaned


def create_chat_reply(raw_messages) -> str:
    """Return the concierge's text reply for the given conversation history."""
    api_key = _api_key()
    if not api_key:
        raise ConciergeError('The concierge is not configured yet. Add OPENAI_API_KEY on the server.')

    messages = [{'role': 'system', 'content': CHAT_SYSTEM_PROMPT}] + _clean_messages(raw_messages)

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency guaranteed in prod
        raise ConciergeError('OpenAI package is not installed on the server.') from exc

    client = OpenAI(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model=_chat_model(),
            messages=messages,
            temperature=0.7,
            max_tokens=400,
        )
    except Exception as exc:
        detail = str(exc).strip()
        if settings.DEBUG and detail:
            raise ConciergeError(detail) from exc
        raise ConciergeError('The concierge is unavailable right now. Please try again in a moment.') from exc

    reply = (completion.choices[0].message.content or '').strip()
    if not reply:
        raise ConciergeError('The concierge did not have a response. Please try again.')
    return reply


def create_realtime_session() -> dict:
    """Mint a short-lived ephemeral client secret for a browser WebRTC voice call.

    Returns a dict with the ephemeral ``client_secret`` (safe to expose to the
    browser), the ``model``, and the ``voice``. The long-lived key stays server-side.
    """
    api_key = _api_key()
    if not api_key:
        raise ConciergeError('Voice calls are not configured yet. Add OPENAI_API_KEY on the server.')

    model = _realtime_model()
    voice = _voice()
    payload = json.dumps({
        'session': {
            'type': 'realtime',
            'model': model,
            'instructions': SYSTEM_PROMPT,
            'audio': {
                'input': {
                    # Transcribe the guest's speech so the client can react to what they say.
                    'transcription': {'model': 'whisper-1'},
                },
                'output': {'voice': voice},
            },
        },
    }).encode('utf-8')

    request = urllib.request.Request(
        REALTIME_CLIENT_SECRETS_URL,
        data=payload,
        method='POST',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'OpenAI-Safety-Identifier': 'legacytress-concierge',
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = ''
        try:
            detail = exc.read().decode('utf-8')
        except Exception:  # pragma: no cover - best effort
            detail = str(exc)
        if settings.DEBUG and detail:
            raise ConciergeError(f'Realtime session error: {detail}') from exc
        raise ConciergeError('Could not start a voice session right now. Please try again.') from exc
    except Exception as exc:
        if settings.DEBUG:
            raise ConciergeError(f'Realtime session error: {exc}') from exc
        raise ConciergeError('Could not start a voice session right now. Please try again.') from exc

    # GA response nests the key under client_secret.value; be tolerant of shapes.
    secret = data.get('client_secret')
    if isinstance(secret, dict):
        client_secret = secret.get('value')
        expires_at = secret.get('expires_at')
    else:
        client_secret = data.get('value')
        expires_at = data.get('expires_at')

    if not client_secret:
        raise ConciergeError('The voice service returned an unexpected response. Please try again.')

    return {
        'client_secret': client_secret,
        'expires_at': expires_at,
        'model': model,
        'voice': voice,
    }
