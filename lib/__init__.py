"""tgbot — small reusable Telegram long-polling bot core."""

from __future__ import annotations

from .core import DEFAULT_HELP_TEXT, Bot, load_env

__all__ = ["Bot", "load_env", "DEFAULT_HELP_TEXT"]
