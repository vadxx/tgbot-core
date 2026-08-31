"""Telegram layer: long-polling loop, message routing, sending.

App logic is injected as callbacks — nothing app-specific is imported here:

    bot = Bot(token, password, keyboard_rows=[["⏰ Server time"]])
    bot.run_forever(commands={"/time": on_time}, on_message=on_text)

Built-ins handled by the package: password authorization, /start (including
the `/start <payload>` deep-link form via on_start_payload — the command
message itself is deleted to keep the chat clean), /help,
/subscribe, /unsubscribe (plus the 🔔/🔕 button labels). Chats that have not
authorized yet see a keyboard with only the 🔑 Authorize button.
"""

from __future__ import annotations

import os
import queue
import threading
import time
from collections.abc import Callable, Iterable
from pathlib import Path

import requests

from . import state

_TELEGRAM_HARD_LIMIT = 4000

# The only button shown to chats that have not passed the password yet.
AUTHORIZE_BUTTON = "🔑 Authorize"

# Poll timing: Telegram holds a long-poll up to _POLL_TIMEOUT; the HTTP request
# allows _REQUEST_TIMEOUT; _STALL_LIMIT is the hard cap after which a wedged
# connection is abandoned (its daemon thread is left to die on its own).
_POLL_TIMEOUT = 30
_REQUEST_TIMEOUT = 35
_STALL_LIMIT = 60
_MAX_STALLS = 5

DEFAULT_HELP_TEXT = (
    "<b>Commands</b>\n"
    "/subscribe — receive broadcast messages\n"
    "/unsubscribe — stop broadcast messages\n"
    "/help — show this message\n"
    "\nSend any text or tap a button and the bot will respond."
)

OnMessage = Callable[[str, str, "Bot"], None]
CommandHandler = Callable[[str, "Bot"], None]
OnTick = Callable[["Bot"], None]
OnStartPayload = Callable[[str, str, "Bot"], None]  # (payload, chat_id, bot)


def load_env(path: str = ".env") -> None:
    """Load KEY=VALUE lines from a .env file into os.environ (env wins)."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            # Quoted values keep everything (even "#"); unquoted values treat
            # " #" as an inline comment, so passwords may contain "#".
            if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
                val = val[1:-1]
            else:
                val = val.split(" #", 1)[0].strip()
            if key and key not in os.environ:
                os.environ[key] = val


class Bot:
    """Long-polling Telegram bot with auth, subscriptions and a reply keyboard."""

    @classmethod
    def from_env(cls, env_path: str = ".env", **kwargs) -> "Bot":
        """Build a Bot from TELEGRAM_BOT_TOKEN / BOT_PASSWORD (loads env_path .env first).
        Raises ValueError when TELEGRAM_BOT_TOKEN is not set."""
        load_env(env_path)
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set, cannot run")
        return cls(token, password=os.environ.get("BOT_PASSWORD", ""), **kwargs)

    def __init__(
        self,
        token: str,
        password: str = "",
        out_dir: str | Path = "out",
        keyboard_rows: list[list[str]] | None = None,
        keyboard_provider: Callable[[str], list[list[str]]] | None = None,
        help_text: str = DEFAULT_HELP_TEXT,
        subscribe_reply: str = "✅ You are subscribed to broadcasts.",
        unsubscribe_reply: str = "✅ You are unsubscribed from broadcasts.",
    ) -> None:
        self.token = token
        self.password = password
        self.out_dir = Path(out_dir)
        self.keyboard_provider = keyboard_provider
        self.help_text = help_text
        self.subscribe_reply = subscribe_reply
        self.unsubscribe_reply = unsubscribe_reply
        rows = [list(row) for row in (keyboard_rows or [])]
        rows.append(["🔔 Subscribe", "🔕 Unsubscribe"])
        self._keyboard = {"keyboard": rows, "resize_keyboard": True}
        self._keyboard_locked = {"keyboard": [[AUTHORIZE_BUTTON]], "resize_keyboard": True}
        self.subscribers = state.load_subscribers(self.out_dir)
        self.authorized = state.load_authorized(self.out_dir)
        self._offset = 0
        self._api_base = f"https://api.telegram.org/bot{token}"

    def is_authorized(self, chat_id: str) -> bool:
        """True if the chat passed the password (or no password is set)."""
        return state.is_authorized(chat_id, self.authorized, self.password)

    def _keyboard_for(self, chat_id: str) -> dict:
        """Full keyboard for authorized chats; just the Authorize button otherwise.

        When a keyboard_provider is set, authorized chats get whatever rows it
        returns (e.g. a source picker before a source is chosen)."""
        if not self.is_authorized(chat_id):
            return self._keyboard_locked
        if self.keyboard_provider is not None:
            return {"keyboard": self.keyboard_provider(chat_id), "resize_keyboard": True}
        return self._keyboard

    def send(self, chat_id: str, text: str) -> None:
        """Send a message, split at Telegram's length limit, with the keyboard."""
        url = f"{self._api_base}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": self._keyboard_for(chat_id),
        }
        for i in range(0, len(text), _TELEGRAM_HARD_LIMIT):
            payload["text"] = text[i:i + _TELEGRAM_HARD_LIMIT]
            resp = requests.post(url, json=payload, timeout=30)
            if not resp.ok:
                print(f"Telegram send failed for chat {chat_id}: {resp.status_code} {resp.text[:200]}")

    def send_document(self, chat_id: str, path: str | Path, caption: str = "") -> None:
        """Send a file (e.g. an HTML report) via sendDocument.

        Unlike send(), this refuses unauthorized chats: a document is always
        content, never the password prompt."""
        if not self.is_authorized(chat_id):
            print(f"Refused to send document {path} to unauthorized chat {chat_id}")
            return
        url = f"{self._api_base}/sendDocument"
        path = Path(path)
        with open(path, "rb") as f:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (path.name, f)},
                timeout=60,
            )
        if not resp.ok:
            print(f"Telegram sendDocument failed for chat {chat_id}: {resp.status_code} {resp.text[:200]}")

    def broadcast(self, chat_ids: Iterable[str], text: str) -> None:
        """Send a message to every authorized chat, skipping chats that fail."""
        for chat_id in list(chat_ids):
            if not self.is_authorized(chat_id):
                continue
            try:
                self.send(chat_id, text)
            except Exception as e:
                print(f"  Failed to send to {chat_id}: {e}")

    def delete_message(self, chat_id: str, message_id: int) -> None:
        """Best-effort deleteMessage; failures are logged and ignored."""
        try:
            resp = requests.post(
                f"{self._api_base}/deleteMessage",
                json={"chat_id": chat_id, "message_id": message_id},
                timeout=15,
            )
            if not resp.ok:
                print(f"Telegram deleteMessage failed for chat {chat_id}: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"Telegram deleteMessage failed for chat {chat_id}: {e}")

    def get_me(self) -> str:
        """Bot username from getMe ("" on any failure — callers degrade gracefully).

        Handy for building t.me/<username>?start=... deep links."""
        try:
            resp = requests.get(f"{self._api_base}/getMe", timeout=15)
            return resp.json().get("result", {}).get("username", "")
        except Exception:
            return ""

    def _get_updates(self) -> requests.Response:
        """One getUpdates long-poll (30s server-side hold, 35s HTTP timeout)."""
        return requests.get(
            f"{self._api_base}/getUpdates",
            params={"offset": self._offset, "timeout": _POLL_TIMEOUT},
            timeout=_REQUEST_TIMEOUT,
        )

    def run_forever(
        self,
        on_message: OnMessage | None = None,
        commands: dict[str, CommandHandler] | None = None,
        on_tick: OnTick | None = None,
        on_start_payload: OnStartPayload | None = None,
    ) -> int:
        """Poll Telegram forever. Returns non-zero if the network wedges for good.

        `commands` maps a lowercased command or button label ("/time",
        "⏰ server time") to its handler — incoming text is lowercased before
        the lookup, so keys must be lowercase.

        Each poll runs in a daemon thread with a hard time cap: a wedged
        connection (half-open NAT/VPN socket where the read timeout never
        fires) is abandoned and the next poll uses a fresh connection. After
        _MAX_STALLS consecutive stalls the process exits so a container
        restart policy can bring it back clean.
        """
        self.out_dir.mkdir(parents=True, exist_ok=True)

        if self.subscribers:
            self.broadcast(self.subscribers, "🤖 Bot started")

        print("Polling for commands...")

        stalls = 0
        while True:
            try:
                q: queue.Queue = queue.Queue()
                threading.Thread(target=self._poll_into, args=(q,), daemon=True).start()
                try:
                    kind, value = q.get(timeout=_STALL_LIMIT)
                except queue.Empty:
                    stalls += 1
                    print(f"getUpdates stalled > {_STALL_LIMIT}s "
                          f"(stall {stalls}/{_MAX_STALLS}); abandoning the connection")
                    if stalls >= _MAX_STALLS:
                        print("Too many stalled polls; exiting so the runtime can restart the bot")
                        return 1
                    continue
                stalls = 0
                if kind == "err":
                    raise value
                resp = value
                if not resp.ok:
                    print(f"getUpdates failed: {resp.status_code} {resp.text[:200]}")
                    time.sleep(5)
                    continue

                for update in resp.json().get("result", []):
                    self._offset = update["update_id"] + 1
                    msg = update.get("message")
                    if not msg:
                        continue
                    try:
                        self._handle_message(msg, on_message, commands, on_start_payload)
                    except Exception as e:
                        print(f"Error handling message: {e}")

                if on_tick:
                    try:
                        on_tick(self)
                    except Exception as e:
                        print(f"Error in on_tick: {e}")

            except requests.RequestException as e:
                print(f"Poll error: {e}")
                time.sleep(5)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(10)

    def _poll_into(self, q: queue.Queue) -> None:
        """Run one getUpdates and deliver ("ok", response) / ("err", exception) to q."""
        try:
            q.put(("ok", self._get_updates()))
        except BaseException as e:  # forward KeyboardInterrupt too; swallowing it here would hang the main thread until the stall cap
            q.put(("err", e))

    def _handle_message(
        self,
        msg: dict,
        on_message: OnMessage | None = None,
        commands: dict[str, CommandHandler] | None = None,
        on_start_payload: OnStartPayload | None = None,
    ) -> None:
        chat_id = str(msg["chat"]["id"])
        raw_text = (msg.get("text") or "").strip()
        text = raw_text.lower()
        # Slash commands are case-insensitive and may carry an argument
        # ("/start Order_ABC-123"); the argument keeps its case — deep-link
        # payloads are case-sensitive. Plain button texts contain spaces and
        # must stay intact.
        # In groups Telegram clients append the bot username: "/help@MyBot" -> "/help"
        if raw_text.startswith("/"):
            base, _, arg = raw_text.partition(" ")
            cmd = base.split("@", 1)[0].lower()
            arg = arg.strip()
        else:
            cmd, arg = text, ""

        if not state.is_authorized(chat_id, self.authorized, self.password):
            if raw_text == self.password:
                self.send(chat_id, state.authorize(chat_id, self.authorized, self.out_dir))
                # Don't leave the password sitting in the chat history.
                message_id = msg.get("message_id")
                if message_id is not None:
                    self.delete_message(chat_id, message_id)
            else:
                self.send(chat_id, "🔒 This bot is protected. Send the password to authorize.")
            return

        if cmd in ("/start", "/help"):
            if cmd == "/start" and arg and on_start_payload is not None:
                # The client shows the user's "/start <payload>" message in the
                # chat; delete it so deep-link clicks stay clean. Best-effort.
                message_id = msg.get("message_id")
                if message_id is not None:
                    self.delete_message(chat_id, message_id)
                on_start_payload(arg, chat_id, self)
            else:
                self.send(chat_id, self.help_text)

        elif commands and cmd in commands:
            # Checked before the built-in subscription handlers so an app can
            # own the 🔔/🔕 buttons (e.g. per-source subscriptions).
            commands[cmd](chat_id, self)

        elif cmd == "/subscribe" or text == "🔔 subscribe":
            state.subscribe(chat_id, self.subscribers, self.out_dir)
            self.send(chat_id, self.subscribe_reply)

        elif cmd == "/unsubscribe" or text == "🔕 unsubscribe":
            state.unsubscribe(chat_id, self.subscribers, self.out_dir)
            self.send(chat_id, self.unsubscribe_reply)

        elif raw_text and on_message:
            on_message(raw_text, chat_id, self)
