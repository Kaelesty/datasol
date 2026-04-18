"""Interactive read-only terminal UI for Datssol."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from datssol.model import ApiRequestError
from datssol.model import ApiResponseError
from datssol.ui.bootstrap import DEFAULT_PROD_BASE_URL
from datssol.ui.bootstrap import DEFAULT_TEST_BASE_URL
from datssol.ui.bootstrap import build_read_only_interactors
from datssol.ui.bootstrap import resolve_base_url
from datssol.ui.formatters import format_arena
from datssol.ui.formatters import format_logs


@dataclass(slots=True)
class UiSettings:
    token_file: Path = Path(".token")
    timeout_seconds: float = 10.0
    default_server: str = "test"
    initial_logs_tail: int = 20


@dataclass(slots=True)
class UiState:
    server: str
    current_screen: str = "arena"
    logs_tail: int = 20
    last_output: str = ""
    last_error: str | None = None


class ReadOnlyConsoleApp:
    def __init__(self, settings: UiSettings | None = None) -> None:
        self._settings = settings or UiSettings()
        self._state = UiState(
            server=self._settings.default_server,
            current_screen="arena",
            logs_tail=self._settings.initial_logs_tail,
        )

    def run(self) -> int:
        self._refresh_current_screen()

        while True:
            self._render()
            choice = input("> ").strip().lower()

            if choice in {"q", "quit", "exit"}:
                self._clear_screen()
                return 0
            if choice in {"1", "a", "arena"}:
                self._state.current_screen = "arena"
                self._refresh_current_screen()
                continue
            if choice in {"2", "l", "logs"}:
                self._state.current_screen = "logs"
                self._refresh_current_screen()
                continue
            if choice in {"3", "s", "server"}:
                self._toggle_server()
                self._refresh_current_screen()
                continue
            if choice in {"4", "r", "refresh"}:
                self._refresh_current_screen()
                continue
            if choice in {"5", "t", "tail"}:
                self._update_logs_tail()
                continue
            if choice in {"h", "help", "?"}:
                continue

            self._state.last_error = f"Unknown command: {choice!r}"

    def _render(self) -> None:
        self._clear_screen()
        print(self._build_header())
        print()

        if self._state.last_error:
            print(f"Error: {self._state.last_error}")
            print()

        if self._state.last_output:
            print(self._state.last_output)
        else:
            print("No data loaded yet.")

        print()
        print(self._build_menu())

    def _build_header(self) -> str:
        base_url = resolve_base_url(self._state.server, explicit_base_url=None)
        current_label = "Arena" if self._state.current_screen == "arena" else "Logs"
        lines = [
            "DatsSol Read-Only UI",
            f"Screen: {current_label}",
            f"Server: {self._state.server} ({base_url})",
            f"Token file: {self._settings.token_file}",
            f"Logs tail: {self._state.logs_tail}",
            f"Known servers: test={DEFAULT_TEST_BASE_URL}, prod={DEFAULT_PROD_BASE_URL}",
        ]
        return "\n".join(lines)

    def _build_menu(self) -> str:
        return "\n".join(
            [
                "Actions:",
                "  1. Arena",
                "  2. Logs",
                "  3. Switch server (test/prod)",
                "  4. Refresh current screen",
                "  5. Change logs tail",
                "  h. Help / redraw",
                "  q. Quit",
            ]
        )

    def _refresh_current_screen(self) -> None:
        self._state.last_error = None
        try:
            arena_interactor, logs_interactor = build_read_only_interactors(
                token_file=self._settings.token_file,
                server=self._state.server,
                timeout_seconds=self._settings.timeout_seconds,
            )

            if self._state.current_screen == "arena":
                arena = arena_interactor.execute()
                self._state.last_output = format_arena(arena)
                return

            logs = logs_interactor.execute()
            self._state.last_output = format_logs(logs, tail=self._state.logs_tail)
        except (ApiRequestError, ApiResponseError, ValueError) as exc:
            self._state.last_error = str(exc)

    def _toggle_server(self) -> None:
        self._state.server = "prod" if self._state.server == "test" else "test"

    def _update_logs_tail(self) -> None:
        raw_value = input("New logs tail (0 = all): ").strip()
        if not raw_value:
            self._state.last_error = "Logs tail update cancelled."
            return

        try:
            tail = int(raw_value)
        except ValueError:
            self._state.last_error = f"Invalid integer value: {raw_value!r}"
            return

        if tail < 0:
            self._state.last_error = "Logs tail must be >= 0."
            return

        self._state.logs_tail = tail
        if self._state.current_screen == "logs":
            self._refresh_current_screen()
        else:
            self._state.last_error = None

    @staticmethod
    def _clear_screen() -> None:
        os.system("cls" if os.name == "nt" else "clear")


def main() -> int:
    app = ReadOnlyConsoleApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
