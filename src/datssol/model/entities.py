"""Core immutable models used across the project."""

from __future__ import annotations

from dataclasses import dataclass, field


EntityId = str


@dataclass(slots=True, frozen=True)
class Point:
    x: int
    y: int

    def to_api(self) -> list[int]:
        return [self.x, self.y]


@dataclass(slots=True, frozen=True)
class MapSize:
    width: int
    height: int


@dataclass(slots=True, frozen=True)
class Plantation:
    id: EntityId
    position: Point
    is_main: bool
    is_isolated: bool
    immunity_until_turn: int | None
    hp: int


@dataclass(slots=True, frozen=True)
class EnemyPlantation:
    id: EntityId
    position: Point
    hp: int


@dataclass(slots=True, frozen=True)
class Cell:
    position: Point
    terraformation_progress: float
    turns_until_degradation: int | None


@dataclass(slots=True, frozen=True)
class Construction:
    position: Point
    progress: float


@dataclass(slots=True, frozen=True)
class BeaverTarget:
    id: EntityId
    position: Point
    hp: int


@dataclass(slots=True, frozen=True)
class UpgradeTier:
    name: str
    current: int
    max: int


@dataclass(slots=True, frozen=True)
class PlantationUpgrades:
    points: int
    interval_turns: int
    turns_until_points: int
    max_points: int
    tiers: tuple[UpgradeTier, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class MeteoForecast:
    kind: str
    turns_until: int | None = None
    id: EntityId | None = None
    forming: bool | None = None
    position: Point | None = None
    next_position: Point | None = None
    radius: int | None = None


@dataclass(slots=True, frozen=True)
class ArenaState:
    turn_no: int
    next_turn_in: float
    size: MapSize
    action_range: int
    plantations: tuple[Plantation, ...] = field(default_factory=tuple)
    enemy: tuple[EnemyPlantation, ...] = field(default_factory=tuple)
    mountains: tuple[Point, ...] = field(default_factory=tuple)
    cells: tuple[Cell, ...] = field(default_factory=tuple)
    construction: tuple[Construction, ...] = field(default_factory=tuple)
    beavers: tuple[BeaverTarget, ...] = field(default_factory=tuple)
    plantation_upgrades: PlantationUpgrades | None = None
    meteo_forecasts: tuple[MeteoForecast, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ActionPath:
    author: Point
    exit_point: Point
    target: Point

    def to_api(self) -> list[list[int]]:
        return [
            self.author.to_api(),
            self.exit_point.to_api(),
            self.target.to_api(),
        ]


@dataclass(slots=True, frozen=True)
class PlantationAction:
    path: ActionPath

    def to_api(self) -> dict[str, list[list[int]]]:
        return {"path": self.path.to_api()}


@dataclass(slots=True, frozen=True)
class RelocateMainPath:
    from_point: Point
    to_point: Point

    def to_api(self) -> list[list[int]]:
        return [self.from_point.to_api(), self.to_point.to_api()]


@dataclass(slots=True, frozen=True)
class CommandRequest:
    command: tuple[PlantationAction, ...] = field(default_factory=tuple)
    plantation_upgrade: str | None = None
    relocate_main: RelocateMainPath | None = None

    def has_useful_action(self) -> bool:
        return bool(self.command or self.plantation_upgrade or self.relocate_main)


@dataclass(slots=True, frozen=True)
class ApiErrorPayload:
    code: int | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)
    status_code: int | None = None


@dataclass(slots=True, frozen=True)
class CommandResponse:
    code: int
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_success(self) -> bool:
        return not self.errors


@dataclass(slots=True, frozen=True)
class LogEntry:
    time: str
    message: str


@dataclass(slots=True, frozen=True)
class LogsResponse:
    entries: tuple[LogEntry, ...] = field(default_factory=tuple)
    error: ApiErrorPayload | None = None


@dataclass(slots=True, frozen=True)
class ApiConfig:
    base_url: str
    auth_token: str
    timeout_seconds: float = 5.0
    verify_ssl: bool = True
