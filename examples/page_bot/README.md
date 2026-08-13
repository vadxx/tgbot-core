# page bot

Runnable example bot built on the `tgbot` package (the repo's `lib/`, imported
as `tgbot` via `package-dir` in pyproject). Demonstrates a 🌐 Open page button:
the bot sends `web/index.html` (a self-contained HTML+JS page) as a document
via `send_document()` — Telegram offers to open it in the browser. No web
server, no hosting, no HTTPS tunnel needed.

## Setup

```bash
# from the repo root
python -m venv venv           # do once
source venv/Scripts/activate  # do in every new terminal session
pip install -e .              # do once — installs the tgbot package
```

## Use

```bash
# from this directory
cp config/.env.example .env   # then edit .env with your real token
python handlers.py "hi"       # test response logic without Telegram
python bot.py                 # run the bot (Ctrl+C to stop)
```

## Docker

```bash
docker compose up -d --build
docker compose logs -f        # should show "Polling for commands..."
```

Message the bot and tap 🌐 Open page — the bot replies with `index.html`;
open it in a browser.

The build context is the repo root (`../..`), because the image installs the
`tgbot` package from there. `./out` is mounted as a volume so subscribers and
authorized chats survive restarts.
