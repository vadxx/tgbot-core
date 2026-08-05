"""Message handlers: turn user input text into bot responses.

bot.py calls get_response() for every message that is not a built-in command
(/start, /help, /subscribe, /unsubscribe). Add your own logic here — this
module has no Telegram dependencies and can be tested standalone:

    python handlers.py "some user message"

Reply-keyboard buttons: BUTTONS lists the button labels shown to the user.
A button press arrives as a plain text message, so handle each label in
get_response() below. bot.py reads BUTTONS to build the keyboard.
"""

from __future__ import annotations

import html
import sys
from datetime import datetime

# Reply-keyboard buttons (one row). Handled in get_response() below.
BUTTONS = ["ℹ️ About", "⏰ Server time"]


def get_response(text: str, chat_id: str = "") -> str:
    """Return the bot's reply for a free-text message or a button press."""
    t = text.strip().lower()

    # --- button handlers ---
    if t == "ℹ️ about":
        return "🤖 A Telegram bot skeleton. Send a message or tap a button."

    if t == "⏰ server time":
        return f"🕐 Server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # --- free-text handlers ---
    if t in ("hi", "hello", "hey", "привет"):
        return "Hello! Send me a message and I will respond."

    # Default: echo back what the user said (HTML-escaped for parse_mode=HTML).
    return f"You said: {html.escape(text)}"


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    message = " ".join(sys.argv[1:]) or "hello"
    print(get_response(message))
