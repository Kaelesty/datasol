"""Application bootstrap for the read-only CLI."""

from __future__ import annotations

from pathlib import Path

from datssol.data import GetArenaInteractor
from datssol.data import GetLogsInteractor
from datssol.data import RequestsGameApiGateway
from datssol.data import SubmitCommandInteractor
from datssol.data import load_token
from datssol.model import ApiConfig

DEFAULT_TEST_BASE_URL = "https://games-test.datsteam.dev"
DEFAULT_PROD_BASE_URL = "https://games.datsteam.dev"


def resolve_base_url(server: str | None, explicit_base_url: str | None) -> str:
    if explicit_base_url:
        return explicit_base_url
    if server == "prod":
        return DEFAULT_PROD_BASE_URL
    return DEFAULT_TEST_BASE_URL


def build_read_only_interactors(
    *,
    token_file: str | Path,
    server: str = "test",
    base_url: str | None = None,
    timeout_seconds: float = 10.0,
) -> tuple[GetArenaInteractor, GetLogsInteractor]:
    config = ApiConfig(
        base_url=resolve_base_url(server, base_url),
        auth_token=load_token(token_file),
        timeout_seconds=timeout_seconds,
    )
    gateway = RequestsGameApiGateway(config)
    return GetArenaInteractor(gateway), GetLogsInteractor(gateway)


def build_bot_interactors(
    *,
    token_file: str | Path,
    server: str = "test",
    base_url: str | None = None,
    timeout_seconds: float = 10.0,
) -> tuple[GetArenaInteractor, SubmitCommandInteractor]:
    config = ApiConfig(
        base_url=resolve_base_url(server, base_url),
        auth_token=load_token(token_file),
        timeout_seconds=timeout_seconds,
    )
    gateway = RequestsGameApiGateway(config)
    return GetArenaInteractor(gateway), SubmitCommandInteractor(gateway)
