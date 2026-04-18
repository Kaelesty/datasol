"""Flask application for the read-only Datssol web UI."""

from __future__ import annotations

import atexit
import threading
import time
import webbrowser
from pathlib import Path

from datssol.bot import BotConfig
from datssol.bot import BotRunner
from datssol.bot import DEFAULT_PROFILE
from datssol.bot import SUPPORTED_PROFILES
from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request

from datssol.model import ApiRequestError
from datssol.model import ApiResponseError
from datssol.ui.bootstrap import DEFAULT_PROD_BASE_URL
from datssol.ui.bootstrap import DEFAULT_TEST_BASE_URL
from datssol.ui.bootstrap import build_bot_interactors
from datssol.ui.bootstrap import build_read_only_interactors
from datssol.ui.web_presenters import arena_to_payload
from datssol.ui.web_presenters import bot_state_to_payload
from datssol.ui.web_presenters import logs_to_payload

APP_HOST = "127.0.0.1"
APP_PORT = 8765
TOKEN_FILE = Path(".token")
REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_SERVER = "test"
DEFAULT_LOGS_TAIL = 20
DEFAULT_BOT_PROFILE = DEFAULT_PROFILE


def create_app(bot_runner: BotRunner | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    controller = bot_runner or BotRunner(
        config=BotConfig(
            token_file=TOKEN_FILE,
            timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            poll_interval_seconds=0.08,
        ),
        interactor_factory=lambda server: build_bot_interactors(
            token_file=TOKEN_FILE,
            server=server,
            timeout_seconds=REQUEST_TIMEOUT_SECONDS,
        ),
    )
    app.config["BOT_RUNNER"] = controller
    atexit.register(controller.stop)

    @app.get("/")
    def index() -> str:
        return render_template(
            "index.html",
            app_title="DatsSol Command Deck",
            default_server=DEFAULT_SERVER,
            default_logs_tail=DEFAULT_LOGS_TAIL,
            default_bot_profile=DEFAULT_BOT_PROFILE,
            servers={
                "test": DEFAULT_TEST_BASE_URL,
                "prod": DEFAULT_PROD_BASE_URL,
            },
            bot_profiles=SUPPORTED_PROFILES,
        )

    @app.get("/api/ui/meta")
    def meta():
        return jsonify(
            {
                "ok": True,
                "data": {
                    "defaultServer": DEFAULT_SERVER,
                    "defaultLogsTail": DEFAULT_LOGS_TAIL,
                    "defaultBotProfile": DEFAULT_BOT_PROFILE,
                    "botProfiles": list(SUPPORTED_PROFILES),
                    "servers": {
                        "test": DEFAULT_TEST_BASE_URL,
                        "prod": DEFAULT_PROD_BASE_URL,
                    },
                },
            }
        )

    @app.get("/api/ui/arena")
    def arena():
        server = _normalized_server(request.args.get("server"))
        try:
            arena_interactor, _ = build_read_only_interactors(
                token_file=TOKEN_FILE,
                server=server,
                timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            )
            state = arena_interactor.execute()
        except (ApiRequestError, ApiResponseError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc), "server": server})

        return jsonify({"ok": True, "server": server, "data": arena_to_payload(state)})

    @app.get("/api/ui/logs")
    def logs():
        server = _normalized_server(request.args.get("server"))
        tail = _normalized_tail(request.args.get("tail"))
        try:
            _, logs_interactor = build_read_only_interactors(
                token_file=TOKEN_FILE,
                server=server,
                timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            )
            response = logs_interactor.execute()
        except (ApiRequestError, ApiResponseError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc), "server": server, "tail": tail})

        return jsonify(
            {
                "ok": True,
                "server": server,
                "tail": tail,
                "data": logs_to_payload(response, tail=tail),
            }
        )

    @app.get("/api/ui/bot/state")
    def bot_state():
        return jsonify({"ok": True, "data": bot_state_to_payload(controller.get_state())})

    @app.post("/api/ui/bot/control")
    def bot_control():
        payload = request.get_json(silent=True) or {}
        action = str(payload.get("action", "")).strip().lower()

        try:
            if action == "start":
                server = _normalized_server(payload.get("server"))
                profile = payload.get("profile")
                allow_prod = bool(payload.get("allowProd"))
                state = controller.start(server=server, profile=profile, allow_prod=allow_prod)
            elif action == "stop":
                state = controller.stop()
            elif action == "set_profile":
                state = controller.set_profile(payload.get("profile"))
            elif action == "set_server":
                state = controller.set_server(_normalized_server(payload.get("server")))
            else:
                return jsonify({"ok": False, "error": f"Unsupported bot control action: {action!r}"}), 400
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

        return jsonify({"ok": True, "data": bot_state_to_payload(state)})

    return app


def main() -> int:
    app = create_app()
    url = f"http://{APP_HOST}:{APP_PORT}"
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    app.run(host=APP_HOST, port=APP_PORT, debug=False, use_reloader=False)
    return 0


def _open_browser(url: str) -> None:
    time.sleep(0.8)
    webbrowser.open(url)


def _normalized_server(raw_server: str | None) -> str:
    return raw_server if raw_server in {"test", "prod"} else DEFAULT_SERVER


def _normalized_tail(raw_tail: str | None) -> int:
    if raw_tail is None:
        return DEFAULT_LOGS_TAIL
    try:
        tail = int(raw_tail)
    except ValueError:
        return DEFAULT_LOGS_TAIL
    return max(0, tail)
