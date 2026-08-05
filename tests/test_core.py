"""Tests for tgbot.core and tgbot.state. All Telegram calls are mocked."""

from __future__ import annotations

import json

import pytest

from tgbot import state
from tgbot.core import Bot


class _Resp:
    """Minimal stand-in for requests.Response."""

    def __init__(self, ok: bool = True, payload: dict | None = None) -> None:
        self.ok = ok
        self.status_code = 200 if ok else 500
        self.text = "" if ok else "error"
        self._payload = payload or {"result": []}

    def json(self) -> dict:
        return self._payload


class RecBot(Bot):
    """Bot whose send() records instead of hitting Telegram."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sent: list[tuple[str, str]] = []

    def send(self, chat_id: str, text: str) -> None:
        self.sent.append((chat_id, text))


def _msg(text: str, chat_id: int = 123) -> dict:
    return {"chat": {"id": chat_id}, "text": text}


def _keyboard_interrupt(*a, **k):
    """Fake requests.get that stops run_forever() on the first poll."""
    raise KeyboardInterrupt


# --- password auth flow ---


def test_wrong_text_gets_lock_message(tmp_path):
    bot = RecBot(token="test", password="secret", out_dir=tmp_path)
    bot._handle_message(_msg("hello"))
    assert bot.sent == [("123", "🔒 This bot is protected. Send the password to authorize.")]
    assert bot.authorized == set()


def test_correct_password_authorizes_and_persists(tmp_path):
    bot = RecBot(token="test", password="secret", out_dir=tmp_path)
    bot._handle_message(_msg("secret"))
    assert bot.sent == [("123", "✅ Authorized. Use /help to see available commands.")]
    assert "123" in bot.authorized
    assert json.loads((tmp_path / "authorized.json").read_text(encoding="utf-8")) == ["123"]
    # once authorized, normal routing applies
    bot._handle_message(_msg("/help"))
    assert bot.sent[-1] == ("123", bot.help_text)


def test_empty_password_means_open_access(tmp_path):
    seen = []
    bot = RecBot(token="test", password="", out_dir=tmp_path)
    bot._handle_message(_msg("hello"), on_message=lambda t, c, b: seen.append(t))
    assert seen == ["hello"]
    assert bot.sent == []  # no lock message


# --- subscribe / unsubscribe round-trip ---


def test_subscribe_unsubscribe_roundtrip_persists(tmp_path):
    bot = RecBot(token="test", out_dir=tmp_path)
    bot._handle_message(_msg("/subscribe"))
    assert "123" in bot.subscribers
    assert json.loads((tmp_path / "subscribers.json").read_text(encoding="utf-8")) == ["123"]

    bot._handle_message(_msg("🔕 Unsubscribe"))
    assert bot.subscribers == set()
    assert json.loads((tmp_path / "subscribers.json").read_text(encoding="utf-8")) == []


def test_subscribe_button_label(tmp_path):
    bot = RecBot(token="test", out_dir=tmp_path)
    bot._handle_message(_msg("🔔 Subscribe"))
    assert "123" in bot.subscribers
    assert bot.sent == [("123", "✅ You are subscribed to broadcasts.")]


def test_custom_subscribe_replies(tmp_path):
    bot = RecBot(token="test", out_dir=tmp_path,
                 subscribe_reply="✅ You are subscribed to alerts.",
                 unsubscribe_reply="✅ You are unsubscribed from alerts.")
    bot._handle_message(_msg("/subscribe"))
    bot._handle_message(_msg("/unsubscribe"))
    assert bot.sent == [
        ("123", "✅ You are subscribed to alerts."),
        ("123", "✅ You are unsubscribed from alerts."),
    ]


# --- command routing ---


def test_registered_command_fires_and_at_suffix_is_stripped(tmp_path):
    fired = []
    bot = RecBot(token="test", out_dir=tmp_path)
    commands = {"/check": lambda chat_id, b: fired.append(chat_id)}
    bot._handle_message(_msg("/check"), commands=commands)
    bot._handle_message(_msg("/check@MyBot"), commands=commands)  # group mention form
    assert fired == ["123", "123"]
    assert bot.sent == []  # command replaced the default reply


def test_unknown_free_text_goes_to_on_message(tmp_path):
    seen = []
    bot = RecBot(token="test", out_dir=tmp_path)
    bot._handle_message(_msg("what time is it"), commands={}, on_message=lambda t, c, b: seen.append((t, c)))
    assert seen == [("what time is it", "123")]


def test_unmatched_slash_command_falls_back_to_on_message(tmp_path):
    seen = []
    bot = RecBot(token="test", out_dir=tmp_path)
    bot._handle_message(_msg("/nope"), commands={"/check": lambda c, b: None}, on_message=lambda t, c, b: seen.append(t))
    assert seen == ["/nope"]


# --- send() chunking ---


def test_send_chunks_long_messages(monkeypatch, tmp_path):
    posts = []
    monkeypatch.setattr("tgbot.core.requests.post", lambda url, json, timeout: posts.append(dict(json)) or _Resp())
    bot = Bot(token="test", out_dir=tmp_path)
    bot.send("123", "x" * 9000)
    assert [len(p["text"]) for p in posts] == [4000, 4000, 1000]
    assert all(p["chat_id"] == "123" and p["parse_mode"] == "HTML" for p in posts)
    # keyboard: app rows first, subscribe row appended by the package
    bot2 = Bot(token="test", out_dir=tmp_path, keyboard_rows=[["A", "B"]])
    assert bot2._keyboard["keyboard"] == [["A", "B"], ["🔔 Subscribe", "🔕 Unsubscribe"]]


# --- state load/save ---


def test_state_roundtrip_and_corrupt_tolerance(tmp_path):
    assert state.load_subscribers(tmp_path) == set()  # missing file
    subs = state.subscribe("1", set(), tmp_path)
    assert subs == "✅ You are subscribed to broadcasts."
    assert state.load_subscribers(tmp_path) == {"1"}

    (tmp_path / "authorized.json").write_text("not json", encoding="utf-8")
    assert state.load_authorized(tmp_path) == set()  # corrupt file tolerated

    (tmp_path / "authorized.json").write_text('{"a": 1}', encoding="utf-8")
    assert state.load_authorized(tmp_path) == set()  # non-list JSON tolerated


# --- Bot.from_env ---


def test_from_env_reads_token_and_password_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("BOT_PASSWORD", raising=False)
    env = tmp_path / ".env"
    env.write_text("TELEGRAM_BOT_TOKEN=tok123\nBOT_PASSWORD=pw\n", encoding="utf-8")
    bot = Bot.from_env(str(env), out_dir=tmp_path)
    assert bot.token == "tok123"
    assert bot.password == "pw"


def test_from_env_raises_when_token_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN not set, cannot run"):
        Bot.from_env(str(tmp_path / ".env"), out_dir=tmp_path)


def test_from_env_env_vars_win_over_dotenv(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "real-env-token")
    monkeypatch.delenv("BOT_PASSWORD", raising=False)
    env = tmp_path / ".env"
    env.write_text("TELEGRAM_BOT_TOKEN=file-token\nBOT_PASSWORD=file-pw\n", encoding="utf-8")
    bot = Bot.from_env(str(env), out_dir=tmp_path)
    assert bot.token == "real-env-token"  # load_env never overrides existing keys
    assert bot.password == "file-pw"


# --- poll loop stall watchdog ---


def test_stalled_polls_exit_after_max_stalls(tmp_path, monkeypatch):
    """A getUpdates that never returns is abandoned; after _MAX_STALLS the loop exits."""
    import time as _time

    import tgbot.core as core

    monkeypatch.setattr(core, "_STALL_LIMIT", 0.2)
    monkeypatch.setattr(core, "_MAX_STALLS", 3)
    monkeypatch.setattr("tgbot.core.requests.get", lambda *a, **k: _time.sleep(30))

    bot = RecBot(token="test", out_dir=tmp_path)
    assert bot.run_forever() == 1


def test_stall_then_recovery_processes_updates(tmp_path, monkeypatch):
    """After one stall the loop recovers on a fresh connection and handles updates."""
    import time as _time

    import tgbot.core as core

    monkeypatch.setattr(core, "_STALL_LIMIT", 0.2)

    calls = {"n": 0}
    seen = []

    def fake_get(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            _time.sleep(30)  # wedged connection
        if calls["n"] == 2:
            return _Resp(payload={"result": [{"update_id": 1, "message": _msg("/go")}]})
        raise KeyboardInterrupt  # third poll: stop the loop

    monkeypatch.setattr("tgbot.core.requests.get", fake_get)

    bot = RecBot(token="test", out_dir=tmp_path)
    with pytest.raises(KeyboardInterrupt):
        bot.run_forever(commands={"/go": lambda chat_id, b: seen.append(chat_id)})
    assert seen == ["123"]


def test_non_ok_getupdates_is_logged(tmp_path, monkeypatch, capsys):
    import tgbot.core as core

    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(ok=False)
        raise KeyboardInterrupt

    monkeypatch.setattr("tgbot.core.requests.get", fake_get)
    monkeypatch.setattr(core.time, "sleep", lambda s: None)

    bot = RecBot(token="test", out_dir=tmp_path)
    with pytest.raises(KeyboardInterrupt):
        bot.run_forever()
    assert "getUpdates failed: 500" in capsys.readouterr().out


# --- broadcast ---


def test_broadcast_sends_to_all_and_skips_failures(tmp_path, capsys):
    bot = RecBot(token="test", out_dir=tmp_path)

    def flaky_send(chat_id: str, text: str) -> None:
        if chat_id == "bad":
            raise RuntimeError("boom")
        bot.sent.append((chat_id, text))

    bot.send = flaky_send
    bot.broadcast(["a", "bad", "b"], "hi")
    assert bot.sent == [("a", "hi"), ("b", "hi")]  # failure did not stop the rest
    assert "Failed to send to bad: boom" in capsys.readouterr().out


# --- startup broadcast ---


def test_startup_broadcasts_to_existing_subscribers(tmp_path, monkeypatch):
    (tmp_path / "subscribers.json").write_text('["123", "456"]', encoding="utf-8")
    monkeypatch.setattr("tgbot.core.requests.get", _keyboard_interrupt)

    bot = RecBot(token="test", out_dir=tmp_path)
    with pytest.raises(KeyboardInterrupt):
        bot.run_forever()
    assert bot.sent == [("123", "🤖 Bot started"), ("456", "🤖 Bot started")]


def test_no_startup_broadcast_without_subscribers(tmp_path, monkeypatch):
    monkeypatch.setattr("tgbot.core.requests.get", _keyboard_interrupt)

    bot = RecBot(token="test", out_dir=tmp_path)
    with pytest.raises(KeyboardInterrupt):
        bot.run_forever()
    assert bot.sent == []


# --- offset handling ---


def test_offset_advances_past_every_update(tmp_path, monkeypatch):
    """Next poll carries max(update_id)+1, even for updates without a message."""
    offsets = []

    def fake_get(url, params, timeout):
        offsets.append(params["offset"])
        if len(offsets) == 1:
            return _Resp(payload={"result": [
                {"update_id": 41, "message": _msg("/go")},
                {"update_id": 42},  # e.g. edited_message — skipped, still advances
            ]})
        raise KeyboardInterrupt

    monkeypatch.setattr("tgbot.core.requests.get", fake_get)

    bot = RecBot(token="test", out_dir=tmp_path)
    with pytest.raises(KeyboardInterrupt):
        bot.run_forever(commands={"/go": lambda chat_id, b: None})
    assert offsets == [0, 43]


# --- on_tick ---


def test_on_tick_runs_once_per_successful_poll(tmp_path, monkeypatch):
    calls = {"n": 0}
    ticks = []

    def fake_get(*a, **k):
        calls["n"] += 1
        if calls["n"] <= 2:
            return _Resp(payload={"result": []})
        raise KeyboardInterrupt

    monkeypatch.setattr("tgbot.core.requests.get", fake_get)

    bot = RecBot(token="test", out_dir=tmp_path)
    with pytest.raises(KeyboardInterrupt):
        bot.run_forever(on_tick=lambda b: ticks.append(1))
    assert len(ticks) == 2


def test_on_tick_error_is_logged_and_polling_continues(tmp_path, monkeypatch, capsys):
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(payload={"result": []})
        raise KeyboardInterrupt

    def boom(bot):
        raise RuntimeError("tick boom")

    monkeypatch.setattr("tgbot.core.requests.get", fake_get)

    bot = RecBot(token="test", out_dir=tmp_path)
    with pytest.raises(KeyboardInterrupt):
        bot.run_forever(on_tick=boom)
    assert calls["n"] == 2  # loop carried on after the failing tick
    assert "Error in on_tick: tick boom" in capsys.readouterr().out


# --- non-text messages ---


def test_non_text_message_is_ignored(tmp_path):
    seen = []
    bot = RecBot(token="test", out_dir=tmp_path)
    bot._handle_message({"chat": {"id": 123}, "photo": []},
                        on_message=lambda *a: seen.append(a))
    assert seen == []
    assert bot.sent == []


def test_unauthorized_non_text_message_still_gets_lock(tmp_path):
    bot = RecBot(token="test", password="secret", out_dir=tmp_path)
    bot._handle_message({"chat": {"id": 123}, "photo": []})
    assert bot.sent == [("123", "🔒 This bot is protected. Send the password to authorize.")]


# --- handler error isolation ---


def test_failing_command_does_not_stop_the_batch(tmp_path, monkeypatch, capsys):
    calls = {"n": 0}
    seen = []

    def fake_get(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(payload={"result": [
                {"update_id": 1, "message": _msg("/boom")},
                {"update_id": 2, "message": _msg("/go")},
            ]})
        raise KeyboardInterrupt

    def boom(chat_id, bot):
        raise RuntimeError("handler boom")

    monkeypatch.setattr("tgbot.core.requests.get", fake_get)

    bot = RecBot(token="test", out_dir=tmp_path)
    with pytest.raises(KeyboardInterrupt):
        bot.run_forever(commands={"/boom": boom, "/go": lambda chat_id, b: seen.append(chat_id)})
    assert seen == ["123"]  # second update in the batch was still processed
    assert "Error handling message: handler boom" in capsys.readouterr().out


# --- /start ---


def test_start_returns_help_text(tmp_path):
    bot = RecBot(token="test", out_dir=tmp_path)
    bot._handle_message(_msg("/start"))
    assert bot.sent == [("123", bot.help_text)]


# --- send() failure logging ---


def test_send_logs_telegram_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("tgbot.core.requests.post", lambda *a, **k: _Resp(ok=False))
    bot = Bot(token="test", out_dir=tmp_path)
    bot.send("123", "hi")
    assert "Telegram send failed for chat 123: 500" in capsys.readouterr().out
