"""Stable interfaces between the model and data layers."""

from __future__ import annotations

from typing import Protocol

from datssol.model.entities import ArenaState, CommandRequest, CommandResponse, LogsResponse


class ArenaGateway(Protocol):
    def get_arena(self) -> ArenaState:
        """Return the current arena state."""


class CommandGateway(Protocol):
    def submit_command(self, request: CommandRequest) -> CommandResponse:
        """Submit commands for the current turn."""


class LogsGateway(Protocol):
    def get_logs(self) -> LogsResponse:
        """Return player logs."""


class GameApiGateway(ArenaGateway, CommandGateway, LogsGateway, Protocol):
    """Aggregate gateway for all currently known API methods."""

