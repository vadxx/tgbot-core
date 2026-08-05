#!/usr/bin/env bash
# Pack a deploy archive for the echo bot; the packing machinery lives in the
# repo root (pack-release.sh, shared with sibling bots like ../fonds).
set -euo pipefail
cd "$(dirname "$0")/.."
../../pack-release.sh echo-bot.tar.gz \
  bot.py handlers.py
