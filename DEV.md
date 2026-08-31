# Development

## Layout

- `lib/` — the package (installed as `tgbot`): `core.py` (`Bot`, `load_env`),
  `state.py` (authorized/subscribers JSON persistence under `out/`)
- `examples/echo_bot/` — self-contained demo bot (`config/`, `deploy/`,
  `Dockerfile`, `docker-compose.yml`) — see its [README](examples/echo_bot/README.md)
- `examples/page_bot/` — demo bot sending a self-contained HTML/JS page via
  `send_document()` — see its [README](examples/page_bot/README.md)
- `tests/` — pytest suite, all network mocked
- `docs/` — [architecture](docs/ARCHITECTURE.md), [telegram setup](docs/TELEGRAM.md),
  [deploy](docs/DOCKER.md)

## Setup

```bash
python -m venv venv                      # do once
source venv/Scripts/activate             # Git Bash on Windows; venv/bin/activate on Linux
pip install -e . pytest                  # do once
```

## Tests

```bash
python -m pytest tests/
```

All Telegram network calls are mocked; the suite needs no token and no network.
CI runs the same suite on every push to main and every pull request — see
`.github/workflows/test.yml`.

## Run the echo example manually (without Docker)

```bash
cd examples/echo_bot
cp config/.env.example .env    # then edit .env with your real token
python bot.py                  # run the bot (Ctrl+C to stop)
python handlers.py "hi"        # test response logic without Telegram
```

## Release

`pack-release.sh` is run from a dependent bot project that uses this package,
to assemble a deploy tarball with a fresh copy of it — see the script header
for usage.
