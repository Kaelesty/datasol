"""Requests-based implementation of the game API gateway."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urljoin

import requests

from datssol.model.entities import ApiConfig
from datssol.model.entities import ApiErrorPayload
from datssol.model.entities import ArenaState
from datssol.model.entities import BeaverTarget
from datssol.model.entities import Cell
from datssol.model.entities import CommandRequest
from datssol.model.entities import CommandResponse
from datssol.model.entities import Construction
from datssol.model.entities import EnemyPlantation
from datssol.model.entities import LogEntry
from datssol.model.entities import LogsResponse
from datssol.model.entities import MapSize
from datssol.model.entities import MeteoForecast
from datssol.model.entities import Plantation
from datssol.model.entities import PlantationUpgrades
from datssol.model.entities import Point
from datssol.model.entities import UpgradeTier
from datssol.model.exceptions import ApiRequestError
from datssol.model.exceptions import ApiResponseError
from datssol.model.interfaces import GameApiGateway


class RequestsGameApiGateway(GameApiGateway):
    """HTTP gateway backed by ``requests``."""

    def __init__(
        self,
        config: ApiConfig,
        session: requests.Session | None = None,
    ) -> None:
        self._config = config
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Auth-Token": self._config.auth_token,
            }
        )

    def get_arena(self) -> ArenaState:
        response = self._request_json("GET", "/api/arena")
        if response.error is not None:
            raise ApiRequestError(_format_api_error("GET", response.url, response.error))
        payload = response.payload
        if not isinstance(payload, Mapping):
            raise ApiResponseError("Arena payload must be a JSON object.")
        return _parse_arena(payload)

    def submit_command(self, request: CommandRequest) -> CommandResponse:
        response = self._request_json("POST", "/api/command", json=_encode_command_request(request))
        if response.error is not None:
            raise ApiRequestError(_format_api_error("POST", response.url, response.error))
        payload = response.payload
        if not isinstance(payload, Mapping):
            raise ApiResponseError("Command response must be a JSON object.")
        return _parse_command_response(payload)

    def get_logs(self) -> LogsResponse:
        response = self._request_json("GET", "/api/logs")
        if response.error is not None:
            return LogsResponse(error=response.error)
        payload = response.payload
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            return LogsResponse(entries=tuple(_parse_log_entry(item) for item in payload))
        if isinstance(payload, Mapping):
            return LogsResponse(error=_parse_api_error(payload))
        raise ApiResponseError("Logs response must be a JSON array or a JSON object.")

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
    ) -> "_JsonResponse":
        url = urljoin(f"{self._config.base_url.rstrip('/')}/", path.lstrip("/"))
        try:
            response = self._session.request(
                method=method,
                url=url,
                json=json,
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_ssl,
            )
        except requests.RequestException as exc:
            raise ApiRequestError(f"{method} {url} failed.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiResponseError(f"{method} {url} returned non-JSON content.") from exc

        error = _parse_error_payload(response.status_code, payload)
        return _JsonResponse(url=url, status_code=response.status_code, payload=payload, error=error)


class _JsonResponse:
    def __init__(
        self,
        *,
        url: str,
        status_code: int,
        payload: Any,
        error: ApiErrorPayload | None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.payload = payload
        self.error = error


def _encode_command_request(request: CommandRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if request.command:
        payload["command"] = [action.to_api() for action in request.command]
    if request.plantation_upgrade is not None:
        payload["plantationUpgrade"] = request.plantation_upgrade
    if request.relocate_main is not None:
        payload["relocateMain"] = request.relocate_main.to_api()
    return payload


def _parse_arena(payload: Mapping[str, Any]) -> ArenaState:
    return ArenaState(
        turn_no=_require_int(payload, "turnNo"),
        next_turn_in=_require_float(payload, "nextTurnIn"),
        size=_parse_map_size(_require_sequence(payload, "size")),
        action_range=_require_int(payload, "actionRange"),
        plantations=_parse_tuple(payload.get("plantations", ()), _parse_plantation),
        enemy=_parse_tuple(payload.get("enemy", ()), _parse_enemy_plantation),
        mountains=_parse_tuple(payload.get("mountains", ()), _parse_point),
        cells=_parse_tuple(payload.get("cells", ()), _parse_cell),
        construction=_parse_tuple(payload.get("construction", ()), _parse_construction),
        beavers=_parse_tuple(payload.get("beavers", ()), _parse_beaver),
        plantation_upgrades=_parse_optional_mapping(payload.get("plantationUpgrades"), _parse_plantation_upgrades),
        meteo_forecasts=_parse_tuple(payload.get("meteoForecasts", ()), _parse_meteo_forecast),
    )


def _parse_plantation(payload: Any) -> Plantation:
    mapping = _require_mapping_value(payload, "plantation")
    return Plantation(
        id=_require_entity_id(mapping, "id"),
        position=_parse_point(_require_sequence(mapping, "position")),
        is_main=_require_bool(mapping, "isMain"),
        is_isolated=_require_bool(mapping, "isIsolated"),
        immunity_until_turn=_optional_int(mapping.get("immunityUntilTurn")),
        hp=_require_int(mapping, "hp"),
    )


def _parse_enemy_plantation(payload: Any) -> EnemyPlantation:
    mapping = _require_mapping_value(payload, "enemy plantation")
    return EnemyPlantation(
        id=_require_entity_id(mapping, "id"),
        position=_parse_point(_require_sequence(mapping, "position")),
        hp=_require_int(mapping, "hp"),
        immunity_until_turn=_optional_int(mapping.get("immunityUntilTurn")),
    )


def _parse_cell(payload: Any) -> Cell:
    mapping = _require_mapping_value(payload, "cell")
    return Cell(
        position=_parse_point(_require_sequence(mapping, "position")),
        terraformation_progress=_require_float(mapping, "terraformationProgress"),
        turns_until_degradation=_optional_int(mapping.get("turnsUntilDegradation")),
    )


def _parse_construction(payload: Any) -> Construction:
    mapping = _require_mapping_value(payload, "construction")
    return Construction(
        position=_parse_point(_require_sequence(mapping, "position")),
        progress=_require_float(mapping, "progress"),
    )


def _parse_beaver(payload: Any) -> BeaverTarget:
    mapping = _require_mapping_value(payload, "beaver target")
    return BeaverTarget(
        id=_require_entity_id(mapping, "id"),
        position=_parse_point(_require_sequence(mapping, "position")),
        hp=_require_int(mapping, "hp"),
    )


def _parse_plantation_upgrades(payload: Mapping[str, Any]) -> PlantationUpgrades:
    return PlantationUpgrades(
        points=_require_int(payload, "points"),
        interval_turns=_require_int(payload, "intervalTurns"),
        turns_until_points=_require_int(payload, "turnsUntilPoints"),
        max_points=_require_int(payload, "maxPoints"),
        tiers=_parse_tuple(payload.get("tiers", ()), _parse_upgrade_tier),
    )


def _parse_upgrade_tier(payload: Any) -> UpgradeTier:
    mapping = _require_mapping_value(payload, "upgrade tier")
    return UpgradeTier(
        name=_require_str(mapping, "name"),
        current=_require_int(mapping, "current"),
        max=_require_int(mapping, "max"),
    )


def _parse_meteo_forecast(payload: Any) -> MeteoForecast:
    mapping = _require_mapping_value(payload, "meteo forecast")
    position = mapping.get("position")
    next_position = mapping.get("nextPosition")
    return MeteoForecast(
        kind=_require_str(mapping, "kind"),
        turns_until=_optional_int(mapping.get("turnsUntil")),
        id=_optional_entity_id(mapping.get("id")),
        forming=_optional_bool(mapping.get("forming")),
        position=_parse_optional_point(position),
        next_position=_parse_optional_point(next_position),
        radius=_optional_int(mapping.get("radius")),
    )


def _parse_command_response(payload: Mapping[str, Any]) -> CommandResponse:
    return CommandResponse(
        code=_require_int(payload, "code"),
        errors=_parse_errors(payload.get("errors", ())),
    )


def _parse_log_entry(payload: Any) -> LogEntry:
    mapping = _require_mapping_value(payload, "log entry")
    return LogEntry(
        time=_require_str(mapping, "time"),
        message=_require_str(mapping, "message"),
    )


def _parse_api_error(payload: Mapping[str, Any], status_code: int | None = None) -> ApiErrorPayload:
    if "code" in payload or "errors" in payload:
        return ApiErrorPayload(
            code=_optional_int(payload.get("code")),
            errors=_parse_errors(payload.get("errors", ())),
            status_code=status_code,
        )
    if "errCode" in payload or "error" in payload:
        raw_error = payload.get("error")
        errors = (str(raw_error),) if raw_error is not None else ()
        return ApiErrorPayload(
            code=_optional_int(payload.get("errCode")),
            errors=errors,
            status_code=status_code,
        )
    return ApiErrorPayload(
        code=None,
        errors=(),
        status_code=status_code,
    )


def _parse_error_payload(status_code: int, payload: Any) -> ApiErrorPayload | None:
    if status_code < 400:
        return None
    if isinstance(payload, Mapping):
        parsed = _parse_api_error(payload, status_code=status_code)
        if parsed.errors or parsed.code is not None:
            return parsed
    return ApiErrorPayload(
        code=None,
        errors=(f"HTTP {status_code} returned an unknown error payload.",),
        status_code=status_code,
    )


def _format_api_error(method: str, url: str, error: ApiErrorPayload) -> str:
    details = "; ".join(error.errors) if error.errors else "unknown server error"
    if error.code is not None:
        return f"{method} {url} failed: code={error.code}, {details}"
    return f"{method} {url} failed: {details}"


def _parse_point(payload: Any) -> Point:
    values = _require_sequence_value(payload, "point")
    if len(values) != 2:
        raise ApiResponseError("Point payload must contain exactly two coordinates.")
    return Point(x=_coerce_int(values[0], "point.x"), y=_coerce_int(values[1], "point.y"))


def _parse_optional_point(payload: Any) -> Point | None:
    if payload is None:
        return None
    return _parse_point(payload)


def _parse_map_size(payload: Sequence[Any]) -> MapSize:
    if len(payload) != 2:
        raise ApiResponseError("Map size payload must contain width and height.")
    return MapSize(width=_coerce_int(payload[0], "size.width"), height=_coerce_int(payload[1], "size.height"))


def _parse_tuple(payload: Any, parser: Any) -> tuple[Any, ...]:
    items = _require_sequence_value(payload, "array")
    return tuple(parser(item) for item in items)


def _parse_optional_mapping(payload: Any, parser: Any) -> Any:
    if payload is None:
        return None
    mapping = _require_mapping_value(payload, "object")
    return parser(mapping)


def _parse_errors(payload: Any) -> tuple[str, ...]:
    if payload is None:
        return ()
    values = _require_sequence_value(payload, "errors")
    return tuple(_coerce_str(item, "errors[]") for item in values)


def _require_mapping(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise ApiResponseError(f"Field '{key}' must be a JSON object.")
    return value


def _require_mapping_value(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ApiResponseError(f"{label.capitalize()} must be a JSON object.")
    return value


def _require_sequence(mapping: Mapping[str, Any], key: str) -> Sequence[Any]:
    value = mapping.get(key)
    return _require_sequence_value(value, key)


def _require_sequence_value(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ApiResponseError(f"{label.capitalize()} must be a JSON array.")
    return value


def _require_str(mapping: Mapping[str, Any], key: str) -> str:
    return _coerce_str(mapping.get(key), key)


def _coerce_str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ApiResponseError(f"Field '{label}' must be a string.")
    return value


def _require_int(mapping: Mapping[str, Any], key: str) -> int:
    return _coerce_int(mapping.get(key), key)


def _require_entity_id(mapping: Mapping[str, Any], key: str) -> str:
    return _coerce_entity_id(mapping.get(key), key)


def _coerce_entity_id(value: Any, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ApiResponseError(f"Field '{label}' must be a string or integer identifier.")
    return str(value)


def _coerce_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiResponseError(f"Field '{label}' must be an integer.")
    return value


def _require_float(mapping: Mapping[str, Any], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ApiResponseError(f"Field '{key}' must be numeric.")
    return float(value)


def _require_bool(mapping: Mapping[str, Any], key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ApiResponseError(f"Field '{key}' must be a boolean.")
    return value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return _coerce_int(value, "optional integer")


def _optional_entity_id(value: Any) -> str | None:
    if value is None:
        return None
    return _coerce_entity_id(value, "optional identifier")


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ApiResponseError("Optional boolean field must be a boolean when present.")
    return value
