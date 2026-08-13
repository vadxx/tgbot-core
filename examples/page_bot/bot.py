"""Runnable example: a bot with a button that sends an HTML/JS web page.

Tap 🌐 Open page and the bot replies with web/index.html as a document
(sendDocument) — Telegram offers to open it in the browser. No web server,
no HTTPS tunnel, nothing to host.

    pip install -e .     # from the tgbot project root
    python bot.py        # from this directory
"""

from __future__ import annotations

import sys
from pathlib import Path

from tgbot import Bot

from handlers import BUTTONS, PAGE_BUTTON, get_response

PAGE_PATH = Path(__file__).parent / "web" / "index.html"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        bot = Bot.from_env(keyboard_rows=[BUTTONS])
    except ValueError as e:
        print(e)
        return 1

    def on_message(text: str, chat_id: str, bot: Bot) -> None:
        if text == PAGE_BUTTON:
            bot.send_document(chat_id, PAGE_PATH, caption="🌐 Open this file in your browser.")
        else:
            bot.send(chat_id, get_response(text, chat_id))

    return bot.run_forever(on_message=on_message)


if __name__ == "__main__":
    raise SystemExit(main())
