# Telegram setup

## Get the bot token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts (choose a name and username)
3. BotFather replies with a token like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`
   — this is your `TELEGRAM_BOT_TOKEN`

Put it in `.env` (copy from `config/.env.example`). Environment variables override the
`.env` file if both are set.

## Bot name rules

BotFather enforces these rules at creation time:

- **Name** (display name): free text, up to 64 characters — shown in chats and
  contact lists.
- **Username** (the `@handle`):
  - must end in `bot` (e.g. `@tgbot_bot`, `@tgbot_alerts_bot`)
  - 5–32 characters long
  - only Latin letters (a–z), digits (0–9) and underscores — no spaces
  - case-insensitive and must be globally unique across Telegram

Conventions for this project:

- Pick a short, descriptive username like `@<purpose>_bot` — it is what users
  type and what appears in group mentions (`/help@your_bot`).
- The username cannot be reused if the bot is deleted, so choose carefully —
  both name and username can be changed later via BotFather (`/setname`,
  `/setuserpic`, etc.), but the old username becomes unavailable while taken.
- Keep the display name human-readable ("TgBot Alerts") and the username
  machine-friendly (`@tgbot_alerts_bot`).

## Using the bot with other people

The bot can only send proactive (broadcast) messages to chats that have
contacted it first and subscribed.

### Private chats

1. The person opens the bot in Telegram and presses **Start** (or sends any message).
2. If `BOT_PASSWORD` is set, they send the password to the bot once to authorize.
3. They send `/subscribe` to the bot (or press the **🔔 Subscribe** button).
4. The bot adds their chat to `out/subscribers.json` and can broadcast to them.

To stop broadcasts, the user sends `/unsubscribe` (or presses **🔕 Unsubscribe**).

The reply keyboard also shows the bot's custom buttons (`ℹ️ About`,
`⏰ Server time` in the echo example) — an app passes them as `keyboard_rows`
to `Bot(...)` and answers their presses via the `on_message` callback
(see `examples/echo_bot/handlers.py`).

### Group chats

1. Add the bot to the group.
2. If `BOT_PASSWORD` is set, someone sends the password in the group once to
   authorize the group chat.
3. Any group member sends `/subscribe` in the group.
4. The group chat is added to the subscriber list and receives broadcasts.

### Restricting access

Set `BOT_PASSWORD` in `.env`. Every chat (private or group) must send the
password once before any command works — authorized chats are remembered in
`out/authorized.json`, so the password is only needed once (or again after a
password change). Until a chat is authorized its reply keyboard shows only the
**🔑 Authorize** button (tapping it just re-sends the password prompt); the
full keyboard appears after authorization. Broadcasts (including the startup
notice) and documents are only ever sent to authorized chats — a subscriber
who has not passed the password receives nothing. If `BOT_PASSWORD` is unset,
the bot is open to anyone and always shows the full keyboard.

> **Privacy mode:** Telegram bots have privacy mode enabled by default. Slash
> commands and inline keyboards always work. If you want reply-keyboard buttons
> to work in a group, disable privacy mode via [@BotFather](https://t.me/BotFather)
> (`/setprivacy` → choose your bot → **Disable**).
