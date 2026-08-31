# tgbot-core

Small reusable Telegram long-polling bot core (stdlib + `requests`), plus
runnable example bots.

| Example | What it shows |
| --- | --- |
| [echo_bot](examples/echo_bot/README.md) | Self-contained demo bot app with Docker deploy |
| [page_bot](examples/page_bot/README.md) | Sends an HTML/JS page via `send_document()` |

## Install

```bash
pip install -e .        # from this directory
```

## Usage

```python
from tgbot import Bot

# reads .env (TELEGRAM_BOT_TOKEN, BOT_PASSWORD); raises ValueError if no token
bot = Bot.from_env(keyboard_rows=[["ℹ️ About", "⏰ Server time"]])
bot.run_forever(
    on_message=lambda text, chat_id, bot: bot.send(chat_id, f"You said: {text}"),
)
```

| Built-in | Behavior |
| --- | --- |
| Authorization | Password gate; empty password = open access |
| `/start`, `/help` | Help text; `/start <payload>` deep links go to `on_start_payload` |
| `/subscribe`, `/unsubscribe` | Broadcast list, with 🔔/🔕 keyboard buttons |
| `send_document()` | File reports (authorized chats only) |
| Messaging | Startup broadcast, 4000-char chunking, long-poll with stall recovery |

App logic is injected via the `commands` / `on_message` / `on_tick` /
`on_start_payload` callbacks — see the docstrings in `lib/core.py`.

## Run an example (Docker Compose)

```bash
cd examples/echo_bot
cp config/.env.example .env    # then edit .env with your real token
docker compose up -d --build
docker compose logs -f         # should show "Polling for commands..."
```

| Doc | Topic |
| --- | --- |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design of the polling loop and message routing |
| [TELEGRAM.md](docs/TELEGRAM.md) | Bot setup on the Telegram side |
| [DOCKER.md](docs/DOCKER.md) | Server deployment |
| [DEV.md](DEV.md) | Layout, tests, running without Docker |
