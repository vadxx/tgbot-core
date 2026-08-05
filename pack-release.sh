#!/usr/bin/env bash
# Assemble a self-contained deploy tree in ./release and pack it as an archive.
# Rebuilt from the working tree on every run, so the archive is never stale.
#
# Usage (from a bot project dir that depends on tgbot, e.g. ../fonds):
#   ../tgbot/pack-release.sh <archive.tar.gz> <app-file>...
#
# The bot dir must provide deploy/Dockerfile and deploy/docker-compose.yml
# (flat build variants where the context is the release tree itself);
# the tgbot package is copied fresh from this script's own repo.
set -euo pipefail

archive="$1"; shift
tgbot_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf release
mkdir -p release/tgbot
cp deploy/Dockerfile release/Dockerfile
cp deploy/docker-compose.yml release/docker-compose.yml
cp -r "$@" release/
cp "$tgbot_dir/pyproject.toml" release/tgbot/
cp -r "$tgbot_dir/lib" release/tgbot/
rm -rf release/tgbot/lib/__pycache__

tar czf "$archive" -C release .
echo "$archive ready — scp it together with .env to the server"
