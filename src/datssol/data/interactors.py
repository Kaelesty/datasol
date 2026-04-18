"""Thin use-case style wrappers around the API gateway."""

from __future__ import annotations

from datssol.model.entities import ArenaState
from datssol.model.entities import CommandRequest
from datssol.model.entities import CommandResponse
from datssol.model.entities import LogsResponse
from datssol.model.interfaces import ArenaGateway
from datssol.model.interfaces import CommandGateway
from datssol.model.interfaces import LogsGateway


class GetArenaInteractor:
    def __init__(self, gateway: ArenaGateway) -> None:
        self._gateway = gateway

    def execute(self) -> ArenaState:
        return self._gateway.get_arena()


class SubmitCommandInteractor:
    def __init__(self, gateway: CommandGateway) -> None:
        self._gateway = gateway

    def execute(self, request: CommandRequest) -> CommandResponse:
        return self._gateway.submit_command(request)


class GetLogsInteractor:
    def __init__(self, gateway: LogsGateway) -> None:
        self._gateway = gateway

    def execute(self) -> LogsResponse:
        return self._gateway.get_logs()

