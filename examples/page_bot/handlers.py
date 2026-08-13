"""Message handlers: turn user input text into bot responses.

bot.py calls get_response() for every message that is not a built-in command
(/start, /help, /subscribe, /unsubscribe) and not the 🌐 Open page button
(bot.py intercepts that one and sends the HTML file as a document). Add your
own logic here — this module has no Telegram dependencies and can be tested
standalone:

    python handlers.py "some user message"

Reply-keyboard buttons: BUTTONS lists the button labels shown to the user.
A button press arrives as a plain text message, so handle each label in
get_response() below (or intercept it in bot.py, like PAGE_BUTTON).
bot.py reads BUTTONS to build the keyboard.
"""

from __future__ import annotations

import html
import sys
from datetime import datetime

# The page button: bot.py intercepts it and sends web/index.html as a document.
PAGE_BUTTON = "🌐 Open page"

# Reply-keyboard buttons (one row). Handled in get_response() / bot.py.
BUTTONS = [PAGE_BUTTON, "ℹ️ About", "⏰ Server time"]


def get_response(text: str, chat_id: str = "") -> str:
    """Return the bot's reply for a free-text message or a button press."""
    t = text.strip().lower()

    # --- button handlers ---
    if t == "ℹ️ about":
        return "🤖 Demo bot: tap 🌐 Open page and I'll send you an HTML page."

    if t == "⏰ server time":
        return f"🕐 Server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # --- free-text handlers ---
    if t in ("hi", "hello", "hey", "привет"):
        return "Hello! Tap 🌐 Open page and I'll send you an HTML page."

    return f"You said: {html.escape(text)}"


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    message = " ".join(sys.argv[1:]) or "hello"
    print(get_response(message))
