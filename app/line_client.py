"""Thin LINE Messaging API client.

Written by hand (instead of the SDK) so you can see exactly what LINE expects:
  - verify_signature: prove the request really came from LINE
  - reply_text:       reply to a message using the event's replyToken
  - get_image_bytes:  download an image a user sent
  - get_display_name: look up the client's LINE display name
"""
import base64
import hashlib
import hmac

import httpx

from .config import config

_API = "https://api.line.me/v2/bot"
_DATA_API = "https://api-data.line.me/v2/bot"
_AUTH = {"Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"}


def verify_signature(body: bytes, signature: str) -> bool:
    """LINE signs every webhook with HMAC-SHA256 over the raw body."""
    mac = hmac.new(config.LINE_CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256)
    expected = base64.b64encode(mac.digest()).decode("utf-8")
    return hmac.compare_digest(expected, signature or "")


async def reply_text(reply_token: str, text: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{_API}/message/reply",
            headers={**_AUTH, "Content-Type": "application/json"},
            json={"replyToken": reply_token, "messages": [{"type": "text", "text": text}]},
        )


async def get_image_bytes(message_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{_DATA_API}/message/{message_id}/content", headers=_AUTH)
        r.raise_for_status()
        return r.content


async def get_display_name(user_id: str) -> str:
    if not user_id:
        return ""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{_API}/profile/{user_id}", headers=_AUTH)
            r.raise_for_status()
            name = r.json().get("displayName", "")
            return name
    except Exception as e:
        print(f"[LINE Profile Error] Could not fetch profile for {user_id}: {e}")
        return ""
