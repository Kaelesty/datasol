from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models import area


JsonObject = dict[str, Any]
JsonInput = str | bytes | bytearray | JsonObject


def _to_dict(data: JsonInput) -> JsonObject:
    if isinstance(data, dict):
        return data

    if isinstance(data, (str, bytes, bytearray)):
        parsed_data = json.loads(data)
        if isinstance(parsed_data, dict):
            return parsed_data
        raise ValueError("JSON должен содержать объект на верхнем уровне")

    raise TypeError("Парсер принимает JSON-строку, bytes или dict")


def parse_area(data: JsonInput) -> area:
    return area.from_dict(_to_dict(data))


def parse_json(json_data: str | bytes | bytearray) -> area:
    return parse_area(json_data)


def parse_file(path: str | Path) -> area:
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("JSON-файл должен содержать объект на верхнем уровне")

    return parse_area(data)


def update_area(current_area: area, data: JsonInput) -> area:
    current_area.update(_to_dict(data))
    return current_area


parse = parse_area
