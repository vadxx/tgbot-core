# Docker & Deploy

## Hosting requirements

- **Outbound HTTPS to `api.telegram.org:443`** — polling, not webhooks: no
  inbound ports, public IP or domain needed; works behind NAT. If the network
  blocks Telegram, host on a VPS abroad or use a proxy — see
  [If Telegram is blocked](#if-telegram-is-blocked).
- **Docker with the Compose plugin** — `docker compose version` should work.
  Without Docker, plain Python 3.12 + `pip install -e .` works too.
- **Minimal resources** — one small Python process; ~50 MB RAM, negligible
  CPU/disk. Any cheap VPS or always-on machine will do.
- **Persistent `./out` directory** — mounted into the container; deleting it
  makes the bot forget subscribers and authorized chats.

Quick check from the host before deploying:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.telegram.org   # expect 200/404, not a timeout
```

## Build & run

```bash
cd examples/echo_bot
docker compose up -d --build
```

That's it — `docker-compose.yml` pins the build, `.env` file, restart policy and
the `./out:/app/out` volume. Because Compose resolves the relative `./out` path
itself, this works identically from Git Bash, PowerShell, CMD and Linux shells
(no MSYS path-mangling issues).

The build context is the **repo root** (`context: ../..`), because the image
installs the `tgbot` package from there. The repo root has a `.dockerignore`
that keeps venvs, `out/` state, `.env` secrets and release artifacts out of
the context.

`out/` preserves `subscribers.json` and `authorized.json` so the bot remembers
who is subscribed and who is authorized across restarts.

## Deploy on another machine

`examples/echo_bot/deploy/release.sh` assembles a self-contained `release/`
tree and packs it as `echo-bot.tar.gz` — rebuilt from the working tree on every
run, so it can never go stale. No `.env` secrets or `out/` state are included.

```bash
# on your machine, from examples/echo_bot/
./deploy/release.sh
scp echo-bot.tar.gz .env user@server:       # .env travels separately, over SSH
# scp -r out user@server:                    # only when migrating an existing bot

# on the target (needs Docker with the Compose plugin)
mkdir echo-bot && tar xzf echo-bot.tar.gz -C echo-bot
cd echo-bot && mv ../.env .                  # out/ is created automatically on first start
docker compose up -d --build
docker compose logs -f                        # should show "Polling for commands..."

# later, to update an already-running bot: re-run ./deploy/release.sh, scp the
# new archive over, re-extract into the same directory, then:
docker compose up -d --build                  # state in out/ survives the rebuild
```

The extracted tree is the build context itself: `Dockerfile` and
`docker-compose.yml` inside it come from `examples/echo_bot/deploy/` —
flat build variants, no parent directory or sibling checkout needed on the
target.

Then message the bot in Telegram: password (if `BOT_PASSWORD` is set), `/help`,
subscribe. If the project lives in a git remote, cloning it on the target
replaces the pack/copy steps entirely.

### Dependent bots (fonds, zakupki, ...)

Bots that install `tgbot` as a package can reuse `pack-release.sh` from this
repo instead of hand-rolling the tar command. It copies the app files plus a
fresh `tgbot/` snapshot into a self-contained `release/` tree and packs it:

```bash
# from the bot's directory (needs deploy/Dockerfile + deploy/docker-compose.yml
# there — flat build variants where the release tree is the context)
../tgbot/pack-release.sh my-bot.tar.gz bot.py requirements.txt config/ ...
```

See `fonds/deploy/release.sh` for a working wrapper and `fonds/docs/DOCKER.md`
for the full target-side flow.

## Useful commands

```bash
docker compose logs -f       # follow logs
docker compose restart       # restart the container
docker compose down          # stop and remove the container (state in ./out survives)
docker exec -it tgbot-echo-bot cat /app/out/subscribers.json  # list subscribers
```

## If Telegram is blocked

Deploy on a VPS instead, or uncomment `HTTPS_PROXY` in `.env`:

```env
HTTPS_PROXY=http://your-proxy-host:port
# or SOCKS5 (requires `pip install requests[socks]`):
HTTPS_PROXY=socks5://your-proxy-host:1080
```
