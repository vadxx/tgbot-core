# echo bot

Runnable example bot built on the `tgbot` package (the repo's `lib/`, imported
as `tgbot` via `package-dir` in pyproject). `bot.py` wires
`handlers.get_response`/`BUTTONS` into `tgbot.Bot`; `handlers.py` has no
Telegram dependencies and can be tested standalone.

Same layout as sibling bot apps (e.g. `fonds/`): app files at the top level,
`config/` for the env template, `deploy/` for release packing.

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

The build context is the repo root (`../..`), because the image installs the
`tgbot` package from there. `./out` is mounted as a volume so subscribers and
authorized chats survive restarts.

## Deploy on another machine

`deploy/release.sh` packs a self-contained `echo-bot.tar.gz` (app files + a
fresh `tgbot/` snapshot + the flat build variants from `deploy/`). The packing
machinery is shared: it lives in `pack-release.sh` at the repo root. See
[docs/DOCKER.md](../../docs/DOCKER.md) for the full target-side flow.
