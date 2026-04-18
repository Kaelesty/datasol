from __future__ import annotations

import json
from typing import Any

import requests

from parser import update_area

API_TOKEN = "f4880ea0-29e1-416f-98aa-26c014130bbf"
GET_DATA_URL = "https://games-test.datsteam.dev/api/arena"
SEND_COMMAND_URL = "https://games-test.datsteam.dev/api/command"
GET_LOGS_URL = "https://games-test.datsteam.dev/api/logs"

HEADERS = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Auth-Token': API_TOKEN,
}


def request_info(game_state):
    response = requests.get(GET_DATA_URL, headers=HEADERS)
    response.raise_for_status()
    return update_area(game_state, response.text)


def send_command(command_json: str | dict[str, Any]):
    payload = json.dumps(command_json) if isinstance(command_json, dict) else command_json
    response = requests.post(SEND_COMMAND_URL, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response

def send_logs():
    response = requests.get(GET_LOGS_URL, headers=HEADERS,)
    return response