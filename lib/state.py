"""Authorized/subscriber persistence: plain JSON sets under an out directory.

Each action performs one operation (and persists state) and returns the reply
text to send back. All paths derive from the caller-supplied ``out_dir``.
"""

from __future__ import annotations

import json
from pathlib import Path


def _load_set(path: Path) -> set[str]:
    """Load a JSON list of strings from path; empty set if missing/broken."""
    values: set[str] = set()
    if not path.is_file():
        return values
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            values.update(str(x) for x in data if x)
    except Exception as e:
        print(f"Failed to load {path}: {e}")
    return values


def _save_set(path: Path, values: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sorted(values), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_authorized(out_dir: str | Path) -> set[str]:
    """Return the set of chat IDs authorized to use the bot."""
    return _load_set(Path(out_dir) / "authorized.json")


def load_subscribers(out_dir: str | Path) -> set[str]:
    """Return the set of chat IDs that should receive broadcasts."""
    return _load_set(Path(out_dir) / "subscribers.json")


def is_authorized(chat_id: str, authorized: set[str], bot_password: str) -> bool:
    """True if the chat may use the bot. Empty password means open access."""
    return not bot_password or chat_id in authorized


def authorize(chat_id: str, authorized: set[str], out_dir: str | Path) -> str:
    """Remember the chat as authorized; return the reply text."""
    authorized.add(chat_id)
    _save_set(Path(out_dir) / "authorized.json", authorized)
    return "✅ Authorized. Use /help to see available commands."


def subscribe(chat_id: str, subscribers: set[str], out_dir: str | Path) -> str:
    """Add the chat to the broadcast list; return the reply text."""
    if chat_id not in subscribers:
        subscribers.add(chat_id)
        _save_set(Path(out_dir) / "subscribers.json", subscribers)
    return "✅ You are subscribed to broadcasts."


def unsubscribe(chat_id: str, subscribers: set[str], out_dir: str | Path) -> str:
    """Remove the chat from the broadcast list; return the reply text."""
    if chat_id in subscribers:
        subscribers.discard(chat_id)
        _save_set(Path(out_dir) / "subscribers.json", subscribers)
    return "✅ You are unsubscribed from broadcasts."
