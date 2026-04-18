from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _merge_data(data: Any = None, updates: dict[str, Any] | None = None) -> dict[str, Any]:
    result = dict(data) if isinstance(data, dict) else {}
    updates = updates or {}
    result.update(updates)
    return result


def _position(value: Any) -> list[int]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return [int(value[0]), int(value[1])]
    return [0, 0]


def _int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


class Model:
    @classmethod
    def create_empty(cls):
        return cls()

    @classmethod
    def empty(cls):
        return cls.create_empty()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None):
        return cls.create_empty().update(data)

    def update(self, data: dict[str, Any] | None = None, **updates):
        raise NotImplementedError


def _model_list(value: Any, model_cls: type[Model]) -> list[Model]:
    return [model_cls.from_dict(item) for item in _items(value)]


@dataclass
class plantation(Model):
    id: str = ""
    position: list[int] = field(default_factory=lambda: [0, 0])
    isMain: bool = False
    isIsolated: bool = False
    immunityUntilTurn: int = 0
    hp: int = 0

    def update(self, data: dict[str, Any] | None = None, **updates):
        data = _merge_data(data, updates)

        if "id" in data:
            self.id = _str(data["id"])
        if "position" in data:
            self.position = _position(data["position"])
        if "isMain" in data:
            self.isMain = _bool(data["isMain"])
        if "isIsolated" in data:
            self.isIsolated = _bool(data["isIsolated"])
        if "immunityUntilTurn" in data:
            self.immunityUntilTurn = _int(data["immunityUntilTurn"])
        if "hp" in data:
            self.hp = _int(data["hp"])

        return self


@dataclass
class enemy(Model):
    id: str = ""
    position: list[int] = field(default_factory=lambda: [0, 0])
    hp: int = 0

    def update(self, data: dict[str, Any] | None = None, **updates):
        data = _merge_data(data, updates)

        if "id" in data:
            self.id = _str(data["id"])
        if "position" in data:
            self.position = _position(data["position"])
        if "hp" in data:
            self.hp = _int(data["hp"])

        return self


@dataclass
class mountain(Model):
    position: list[int] = field(default_factory=lambda: [0, 0])

    def update(self, data: Any = None, **updates):
        if data is not None and not isinstance(data, dict):
            data = {"position": data}

        data = _merge_data(data, updates)

        if "position" in data:
            self.position = _position(data["position"])

        return self


@dataclass
class cell(Model):
    position: list[int] = field(default_factory=lambda: [0, 0])
    terraformationProgress: int = 0
    turnsUntilDegradation: int = 0

    def update(self, data: dict[str, Any] | None = None, **updates):
        data = _merge_data(data, updates)

        if "position" in data:
            self.position = _position(data["position"])
        if "terraformationProgress" in data:
            self.terraformationProgress = _int(data["terraformationProgress"])
        if "turnsUntilDegradation" in data:
            self.turnsUntilDegradation = _int(data["turnsUntilDegradation"])

        return self


@dataclass
class construction(Model):
    position: list[int] = field(default_factory=lambda: [0, 0])
    progress: int = 0

    def update(self, data: dict[str, Any] | None = None, **updates):
        data = _merge_data(data, updates)

        if "position" in data:
            self.position = _position(data["position"])
        if "progress" in data:
            self.progress = _int(data["progress"])

        return self


@dataclass
class beaver(Model):
    id: str = ""
    position: list[int] = field(default_factory=lambda: [0, 0])
    hp: int = 0

    def update(self, data: dict[str, Any] | None = None, **updates):
        data = _merge_data(data, updates)

        if "id" in data:
            self.id = _str(data["id"])
        if "position" in data:
            self.position = _position(data["position"])
        if "hp" in data:
            self.hp = _int(data["hp"])

        return self


@dataclass
class plantationUpgrades(Model):
    points: int = 0
    intervalTurns: int = 0
    turnsUntilPoints: int = 0
    maxPoints: int = 0
    tiers: list[tier] = field(default_factory=list)

    @dataclass
    class tier(Model):
        name: str = ""
        current: int = 0
        max: int = 0

        def update(self, data: dict[str, Any] | None = None, **updates):
            data = _merge_data(data, updates)

            if "name" in data:
                self.name = _str(data["name"])
            if "current" in data:
                self.current = _int(data["current"])
            if "max" in data:
                self.max = _int(data["max"])

            return self

    def update(self, data: dict[str, Any] | None = None, **updates):
        data = _merge_data(data, updates)

        if "points" in data:
            self.points = _int(data["points"])
        if "intervalTurns" in data:
            self.intervalTurns = _int(data["intervalTurns"])
        if "turnsUntilPoints" in data:
            self.turnsUntilPoints = _int(data["turnsUntilPoints"])
        if "maxPoints" in data:
            self.maxPoints = _int(data["maxPoints"])
        if "tiers" in data:
            self.tiers = [
                self.tier.from_dict(item)
                for item in _items(data["tiers"])
            ]

        return self


@dataclass
class meteoForecast(Model):
    kind: str = ""
    turnsUntil: int = 0
    id: str = ""
    forming: bool = False
    position: list[int] = field(default_factory=lambda: [0, 0])
    nextPosition: list[int] = field(default_factory=lambda: [0, 0])
    radius: int = 0

    def update(self, data: dict[str, Any] | None = None, **updates):
        data = _merge_data(data, updates)

        if "kind" in data:
            self.kind = _str(data["kind"])
        if "turnsUntil" in data:
            self.turnsUntil = _int(data["turnsUntil"])
        if "id" in data:
            self.id = _str(data["id"])
        if "forming" in data:
            self.forming = _bool(data["forming"])
        if "position" in data:
            self.position = _position(data["position"])
        if "nextPosition" in data:
            self.nextPosition = _position(data["nextPosition"])
        if "radius" in data:
            self.radius = _int(data["radius"])

        return self


@dataclass
class area(Model):
    turnNo: int = 0
    nextTurnIn: int = 0
    size: list[int] = field(default_factory=lambda: [0, 0])
    actionRange: int = 0
    plantations: list[plantation] = field(default_factory=list)
    enemy: list[enemy] = field(default_factory=list)
    mountains: list[mountain] = field(default_factory=list)
    cells: list[cell] = field(default_factory=list)
    construction: list[construction] = field(default_factory=list)
    beavers: list[beaver] = field(default_factory=list)
    plantationUpgrades: plantationUpgrades = field(default_factory=plantationUpgrades.create_empty)
    meteoForecasts: list[meteoForecast] = field(default_factory=list)

    def update(self, data: dict[str, Any] | None = None, **updates):
        data = _merge_data(data, updates)

        if "turnNo" in data:
            self.turnNo = _int(data["turnNo"])
        if "nextTurnIn" in data:
            self.nextTurnIn = _int(data["nextTurnIn"])
        if "size" in data:
            self.size = _position(data["size"])
        if "actionRange" in data:
            self.actionRange = _int(data["actionRange"])
        if "plantations" in data:
            self.plantations = _model_list(data["plantations"], plantation)
        if "enemy" in data:
            self.enemy = _model_list(data["enemy"], enemy)
        if "enemies" in data:
            self.enemy = _model_list(data["enemies"], enemy)
        if "mountains" in data:
            self.mountains = _model_list(data["mountains"], mountain)
        if "cells" in data:
            self.cells = _model_list(data["cells"], cell)
        if "construction" in data:
            self.construction = _model_list(data["construction"], construction)
        if "constructions" in data:
            self.construction = _model_list(data["constructions"], construction)
        if "beavers" in data:
            self.beavers = _model_list(data["beavers"], beaver)
        if "plantationUpgrades" in data:
            self.plantationUpgrades = plantationUpgrades.from_dict(data["plantationUpgrades"])
        if "meteoForecasts" in data:
            self.meteoForecasts = _model_list(data["meteoForecasts"], meteoForecast)

        return self

    def get_main_plantation(self) -> plantation | None:
        for item in self.plantations:
            if item.isMain:
                return item

        return None

    def get_plantation_pos(self, pos) -> plantation | None:
        for item in self.plantations:
            if item.position == pos:
                return item

        return None
    
    def get_cell_pos(self, pos) -> cell | None:
        for item in self.cells:
            if item.position == pos:
                return item

        return None
    
    @property
    def main_plantation(self) -> plantation | None:
        return self.get_main_plantation()

    def get_cell_with_max_terraformation_progress(self) -> cell | None:
        if not self.cells:
            return None

        return max(self.cells, key=lambda item: item.terraformationProgress)

    @property
    def max_terraformation_cell(self) -> cell | None:
        return self.get_cell_with_max_terraformation_progress()

    def get_construction_with_max_progress(self) -> construction | None:
        if not self.construction:
            return None

        return max(self.construction, key=lambda item: item.progress)

    @property
    def max_progress_construction(self) -> construction | None:
        return self.get_construction_with_max_progress()

    def get_new_plantation(self) -> plantation | None:
        if not self.plantations:
            return None

        return max(self.plantations, key=lambda item: item.immunityUntilTurn)

    @property
    def new_plantation(self) -> plantation | None:
        return self.get_new_plantation()

    def get_cell_with_min_progress(self) -> cell | None:
        if not self.cells:
            return None

        return min(self.cells, key=lambda item: item.terraformationProgress)

    @property
    def min_progress_cell(self) -> cell | None:
        return self.get_cell_with_min_progress()

    def get_plantation_with_min_hp(self) -> plantation | None:
        if not self.plantations:
            return None

        return min(self.plantations, key=lambda item: item.hp)

    @property
    def min_hp_plantation(self) -> plantation | None:
        return self.get_plantation_with_min_hp()


Area = area
Plantation = plantation
Enemy = enemy
Mountain = mountain
Cell = cell
Construction = construction
Beaver = beaver
PlantationUpgrades = plantationUpgrades
MeteoForecast = meteoForecast
