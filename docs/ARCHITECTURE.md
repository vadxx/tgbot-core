# Architecture

## Overview

```
Telegram users
      │  (long polling, HTTPS via requests)
      ▼
┌─────────────┐  built-in cmds  ┌────────────────┐
│             │ ──────────────► │ lib/state.py   │
│  lib/core   │                 │ (auth, subs)   │
│  (Bot class,│ ◄────────────── └────────────────┘
│  Telegram   │   reply text           │ reads/writes
│   layer)    │                        ▼
│             │  commands /   ┌─────────────┐   out/ — JSON state,
│             │ ─────────────►│  your app   │   mounted as a
│             │ ◄─────────────│ (callbacks) │   Docker volume
└─────────────┘   reply text  └─────────────┘
```

Single process, no framework: `tgbot.core.Bot` runs the Telegram long-polling
loop (the package sources live in `lib/` and are imported as `tgbot` via the
`package-dir` mapping in `pyproject.toml`). `requests` is used for the
Telegram API. No database — state lives in plain JSON files under `out/`.

## Components

| Component | Responsibility |
|---|---|
| `lib/core.py` | `Bot` class: polling loop, message routing, message sending; `Bot.from_env()` constructor from `TELEGRAM_BOT_TOKEN`/`BOT_PASSWORD`; `load_env()` .env parser; `DEFAULT_HELP_TEXT` |
| `lib/state.py` | Built-in command actions: authorization, subscribe/unsubscribe; owns the JSON-set persistence, parameterized by `out_dir` |
| your app | Callbacks injected into `bot.run_forever()`: `commands` (command/button label → handler), `on_message` (free-text fallback), `on_tick` (once per poll pass). See `examples/echo_bot/` |
| `out/` | Runtime state: `subscribers.json` (broadcast recipients), `authorized.json` (chats that passed `BOT_PASSWORD`) |
| `.env` | Secrets and tuning, never committed; `config/.env.example` documents the variables |
| `examples/echo_bot/Dockerfile` / `docker-compose.yml` | Containerized run of the echo example, see [DOCKER.md](DOCKER.md); `examples/echo_bot/deploy/` holds the flat variants used for release packing |

## Configuration

All configuration comes from environment variables, with `.env` as the local
source (environment variables win if both are set):

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | Bot token from @BotFather |
| `BOT_PASSWORD` | no | If set, users must send it once to authorize |
| `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` | no | Proxy for Telegram API traffic (SOCKS5 needs `pip install requests[socks]`) |

## Runtime behavior

1. `Bot(...)` restores state from `out_dir`; `run_forever()` broadcasts
   `"🤖 Bot started"` to subscribers and starts polling Telegram
   (`getUpdates`, 30 s long poll). Each poll runs in a daemon thread with a
   hard 60 s cap: a wedged connection is abandoned and retried on a fresh one;
   after 5 consecutive stalls `run_forever()` returns 1 so a container restart
   policy can recover the bot. Failed (non-OK) polls are logged.
2. Each message is routed: built-in commands (`/start`, `/help`, `/subscribe`,
   `/unsubscribe` and their buttons) are handled by the package; a registered
   `commands` key (after `@BotName` stripping) calls its handler; everything
   else goes to `on_message(text, chat_id, bot)`.
3. Replies are sent with HTML parse mode, split at Telegram's length limit.
4. If `BOT_PASSWORD` is set, every chat must send the password once; authorized
   chats are remembered in `out/authorized.json` (until the password changes).

## Extending the bot

Don't edit the package for app behavior — inject it: pass `keyboard_rows` and
`help_text` to `Bot(...)`, and `commands` / `on_message` / `on_tick` to
`run_forever()`. `examples/echo_bot/` shows the pattern end to end.

## Design constraints to keep

- **No heavy dependencies** — stdlib + `requests`.
- **State survives restarts** — anything worth remembering goes to `out/`,
  which is a mounted volume in Docker; the container itself is disposable.
- **Telegram concerns stay in `lib/core.py`** — app callbacks take plain data
  and use `bot.send`/`bot.broadcast`, so they stay testable without Telegram.
- **Polling, not webhooks** — no public endpoint needed; works behind NAT and
  through a proxy.
