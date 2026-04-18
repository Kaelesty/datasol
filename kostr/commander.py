from __future__ import annotations

import json
from typing import Any


Position = list[int]
Path = list[Position]
CommandObject = dict[str, Any]


def _position(value: Any) -> Position:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Position must be [x, y]")

    return [int(value[0]), int(value[1])]


def _path(value: Any, expected_length: int, name: str) -> Path:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{name} must contain {expected_length} positions")

    if len(value) != expected_length:
        raise ValueError(f"{name} must contain exactly {expected_length} positions")

    return [_position(position) for position in value]


class CommandAgent:
    def __init__(self):
        self.command_paths: list[Path] = []
        self.plantation_upgrade: str | None = None
        self.relocate_main: Path | None = None

    @classmethod
    def create_empty(cls):
        return cls()

    @classmethod
    def empty(cls):
        return cls.create_empty()

    def add_path(self, path: Any):
        self.command_paths.append(_path(path, 3, "Command path"))
        return self

    def add_paths(self, paths: Any):
        for path in paths:
            self.add_path(path)
        return self

    def set_plantation_upgrade(self, name: str | None):
        if name is None:
            self.plantation_upgrade = None
            return self

        name = str(name)
        if not name:
            raise ValueError("Plantation upgrade name must not be empty")

        self.plantation_upgrade = name
        return self

    def set_relocate_main(self, path: Any | None):
        self.relocate_main = None if path is None else _path(path, 2, "Relocate main")
        return self

    def clear(self):
        self.command_paths.clear()
        self.plantation_upgrade = None
        self.relocate_main = None
        return self

    def build(self) -> CommandObject:
        result: CommandObject = {}

        if self.command_paths:
            result["command"] = [
                {"path": path}
                for path in self.command_paths
            ]

        if self.plantation_upgrade is not None:
            result["plantationUpgrade"] = self.plantation_upgrade

        if self.relocate_main is not None:
            result["relocateMain"] = self.relocate_main

        if not result:
            raise ValueError(
                "Request must contain command, plantationUpgrade or relocateMain"
            )

        return result

    def to_json(self) -> str:
        return json.dumps(self.build())


def create_command(
    command_paths: Any | None = None,
    plantation_upgrade: str | None = None,
    relocate_main: Any | None = None,
) -> CommandObject:
    agent = CommandAgent.create_empty()

    if command_paths:
        agent.add_paths(command_paths)
    if plantation_upgrade is not None:
        agent.set_plantation_upgrade(plantation_upgrade)
    if relocate_main is not None:
        agent.set_relocate_main(relocate_main)

    return agent.build()


def create_command_json(
    command_paths: Any | None = None,
    plantation_upgrade: str | None = None,
    relocate_main: Any | None = None,
) -> str:
    return json.dumps(
        create_command(
            command_paths=command_paths,
            plantation_upgrade=plantation_upgrade,
            relocate_main=relocate_main,
        )
    )


commander = CommandAgent.create_empty()
