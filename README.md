# tgbot-core

Small reusable Telegram long-polling bot core (stdlib + `requests`), plus a
runnable echo-bot example.

## Layout

- `lib/` — the package sources (imported as `tgbot` via `package-dir` in pyproject): `core.py` (`Bot` class, `load_env`), `state.py` (authorized/subscribers JSON persistence under `out/`)
- `examples/echo_bot/` — self-contained demo bot app (same layout as sibling apps like `fonds/`): `bot.py` + `handlers.py` with its own `config/`, `deploy/`, `Dockerfile`, `docker-compose.yml` — see its [README](examples/echo_bot/README.md)
- `tests/` — pytest suite, all network mocked (`python -m pytest tests/`)
- `docs/` — [architecture](docs/ARCHITECTURE.md), [telegram setup](docs/TELEGRAM.md), [deploy](docs/DOCKER.md)

## Install

```bash
pip install -e .        # from this directory
```

## Usage

```python
from tgbot import Bot

# reads .env (TELEGRAM_BOT_TOKEN, BOT_PASSWORD); raises ValueError if no token
bot = Bot.from_env(keyboard_rows=[["🔍 Check now"]])
bot.run_forever(
    commands={"/check": lambda chat_id, bot: bot.send(chat_id, "checking...")},
    on_message=lambda text, chat_id, bot: bot.send(chat_id, f"You said: {text}"),
)
```

Built into the package: password authorization (empty password = open access),
`/start` `/help`, `/subscribe` `/unsubscribe` with 🔔/🔕 keyboard buttons,
`"🤖 Bot started"` broadcast on startup, HTML sending chunked at 4000 chars,
and the long-poll loop with error backoff. App logic is injected via the
`commands` / `on_message` / `on_tick` callbacks — see the docstrings in
`tgbot/core.py` and the full example in `examples/echo_bot/`.

## Run the echo example (Docker Compose)

```bash
cd examples/echo_bot
cp config/.env.example .env    # then edit .env with your real token
docker compose up -d --build
docker compose logs -f         # should show "Polling for commands..."
```

That's it — Compose pins the build, `.env`, restart policy and the `./out`
state volume. Details and server deployment: [docs/DOCKER.md](docs/DOCKER.md).

## Run the echo example manually (without Docker)

```bash
python -m venv venv                        # do once
source venv/Scripts/activate               # do in every new terminal session
pip install -e .                           # do once

cd examples/echo_bot
python bot.py                              # run the bot (Ctrl+C to stop)
python handlers.py "hi"                    # test response logic without Telegram
```
