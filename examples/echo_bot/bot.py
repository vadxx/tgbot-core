"""Runnable example: the original echo bot, rebuilt on the tgbot package.

    pip install -e .     # from the tgbot project root
    python bot.py        # from this directory
"""

from __future__ import annotations

import sys

from tgbot import Bot

from handlers import BUTTONS, get_response


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        bot = Bot.from_env(keyboard_rows=[BUTTONS])
    except ValueError as e:
        print(e)
        return 1

    return bot.run_forever(
        on_message=lambda text, chat_id, bot: bot.send(chat_id, get_response(text, chat_id)),
    )


if __name__ == "__main__":
    raise SystemExit(main())
