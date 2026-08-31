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

- **`lib/core.py`** — `Bot` class: polling loop, message routing, sending;
  `Bot.from_env()` from `TELEGRAM_BOT_TOKEN`/`BOT_PASSWORD`; `load_env()` .env
  parser; `DEFAULT_HELP_TEXT`
- **`lib/state.py`** — built-in command actions (authorization,
  subscribe/unsubscribe); owns JSON-set persistence, parameterized by `out_dir`
- **your app** — callbacks injected into `bot.run_forever()`: `commands`
  (lowercased command/button label → handler; overrides the built-in
  subscribe/unsubscribe), `on_message` (free-text fallback), `on_tick` (once
  per poll pass), `on_start_payload` (`/start <payload>` deep links). See
  `examples/echo_bot/`
- **`out/`** — runtime state: `subscribers.json` (broadcast recipients; apps
  can keep extra named lists), `authorized.json` (chats that passed
  `BOT_PASSWORD`)
- **`.env`** — secrets and tuning, never committed; each example's
  `config/.env.example` documents the variables
- **`examples/echo_bot/Dockerfile` / `docker-compose.yml`** — containerized run
  of the echo example, see [DOCKER.md](DOCKER.md); `examples/echo_bot/deploy/`
  holds the flat variants used for release packing

## Configuration

All configuration comes from environment variables, with `.env` as the local
source (environment variables win if both are set):

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | Bot token from @BotFather |
| `BOT_PASSWORD` | no | If set, users must send it once to authorize |
| `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` | no | Telegram proxy; SOCKS5 needs `requests[socks]` |

## Runtime behavior

1. `Bot(...)` restores state from `out_dir`; `run_forever()` broadcasts
   `"🤖 Bot started"` to subscribers and starts polling Telegram
   (`getUpdates`, 30 s long poll). Each poll runs in a daemon thread with a
   hard 60 s cap: a wedged connection is abandoned and retried on a fresh one;
   after 5 consecutive stalls `run_forever()` returns 1 so a container restart
   policy can recover the bot. Failed (non-OK) polls are logged.
2. Each message is routed in order: `/start`/`/help` (a `/start <payload>`
   deep link goes to `on_start_payload`, and the command message is deleted);
   then a registered `commands` key (lowercased, after `@BotName` stripping)
   calls its handler; then the built-in `/subscribe`/`/unsubscribe` and their
   🔔/🔕 buttons; everything else goes to `on_message(text, chat_id, bot)`.
3. Replies are sent with HTML parse mode, split at Telegram's length limit.
4. If `BOT_PASSWORD` is set, every chat must send the password once (the
   password message is deleted afterwards); authorized chats are remembered in
   `out/authorized.json` (until the password changes).

## Extending the bot

Don't edit the package for app behavior — inject it: pass `keyboard_rows` (or
`keyboard_provider` for per-chat keyboards) and `help_text` to `Bot(...)`, and
`commands` / `on_message` / `on_tick` / `on_start_payload` to `run_forever()`.
`examples/echo_bot/` shows the pattern end to end.

## Design constraints to keep

- **No heavy dependencies** — stdlib + `requests`.
- **State survives restarts** — anything worth remembering goes to `out/`,
  which is a mounted volume in Docker; the container itself is disposable.
- **Telegram concerns stay in `lib/core.py`** — app callbacks take plain data
  and use `bot.send`/`bot.broadcast`, so they stay testable without Telegram.
- **Polling, not webhooks** — no public endpoint needed; works behind NAT and
  through a proxy.
