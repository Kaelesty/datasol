from __future__ import annotations

import time

import rr_lib as rr
from commander import CommandAgent
from models import area


game_state = area.create_empty()
NEIGHBOR_OFFSETS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _first_available_upgrade_name():
    if game_state.plantationUpgrades.points <= 0:
        return None

    for tier in game_state.plantationUpgrades.tiers:
        if tier.current < tier.max:
            return tier.name

    return None


def _position_key(position: list[int]) -> tuple[int, int]:
    return int(position[0]), int(position[1])


def _is_inside_area(position: tuple[int, int]) -> bool:
    width, height = game_state.size
    x, y = position
    return 0 <= x < width and 0 <= y < height


def _occupied_positions() -> set[tuple[int, int]]:
    occupied: set[tuple[int, int]] = set()

    for items in (
        game_state.plantations,
        game_state.enemy,
        game_state.mountains,
        game_state.cells,
        game_state.construction,
        game_state.beavers,
    ):
        for item in items:
            occupied.add(_position_key(item.position))

    for forecast in game_state.meteoForecasts:
        occupied.add(_position_key(forecast.position))
        occupied.add(_position_key(forecast.nextPosition))

    return occupied


def _available_plantation():
    for plantation in game_state.plantations:
        if plantation.hp > 0 and not plantation.isIsolated:
            return plantation

    return None


def _free_neighbor(position: list[int]) -> list[int] | None:
    occupied = _occupied_positions()
    x, y = _position_key(position)

    for dx, dy in NEIGHBOR_OFFSETS:
        neighbor = (x + dx, y + dy)
        if _is_inside_area(neighbor) and neighbor not in occupied:
            return [neighbor[0], neighbor[1]]

    return None


def create_replace_main_command(old, new):
    command = CommandAgent.create_empty()
    return command.set_relocate_main([old, new]).to_json()


def create_turn_command_json(new , _neighbor = None) -> str:
    command = CommandAgent.create_empty()
    if(_neighbor == None):
        neighbor = _free_neighbor(new)
    else:
        neighbor = _neighbor
    if neighbor is not None:
        for item in game_state.plantations:
            if abs(neighbor[0] - item.position[0]) + abs(neighbor[1] - item.position[1]) <=3:
                command.add_path([
                    item.position,
                    new,
                    neighbor,
                ])
        return command.to_json()    

    upgrade_name = _first_available_upgrade_name()
    if upgrade_name is not None:
        return command.set_plantation_upgrade(upgrade_name).to_json()



def run_game_loop(delay_seconds: float = 0.0, max_turns: int | None = None):
    counter = 0;
    rr.request_info(game_state)
    command_json = create_turn_command_json(game_state.get_main_plantation().position)
    plant_size = len(game_state.plantations)
    while max_turns is None or 0 < max_turns:
        print(f"Turn: -- {game_state.turnNo} --")
        print(f"Points: -- {counter} --")
        if(game_state.turnNo>598):
            time.sleep(5)
        rr.request_info(game_state)
        #print(f"new_pos: {game_state.plantations}\n\n")
        if(game_state.get_cell_with_max_terraformation_progress()!=None):
            if(game_state.get_cell_with_max_terraformation_progress().terraformationProgress == 95):
                counter+=1
        if(game_state.get_main_plantation().position != game_state.get_new_plantation().position):
                swap_command_json = create_replace_main_command(game_state.get_main_plantation().position, game_state.new_plantation.position)
                rr.send_command(swap_command_json)
        #print(f"{game_state.construction}")
        if(len(game_state.plantations) != plant_size):
            plant_size = len(game_state.plantations)
            if len(game_state.construction) == 0:
                command_json = create_turn_command_json(game_state.get_main_plantation().position)
            else:
                command_json = create_turn_command_json(game_state.get_main_plantation().position, game_state.construction[0].position)
        if(game_state.get_cell_pos(game_state.get_main_plantation().position).terraformationProgress > 90):
            time.sleep(2.5)
            rr.request_info(game_state)
            command_json = create_turn_command_json(game_state.get_main_plantation().position)
        print(f"newest: {game_state.new_plantation.position}")
        if(len(game_state.cells) !=0):
            for item in game_state.plantations:
                print(f"Main: {item.isMain} ID: {item.position} HP: {item.hp} Terraform: {game_state.get_cell_pos(item.position).terraformationProgress}")
        print(f"SIZE: {len(game_state.plantations)}")
        print(f"Постройка: {game_state.construction}\n")
        #print(f"enemy: {len(game_state.enemy)} | beavers: {len(game_state.beavers)}\n\n")
        print(command_json)
        response = rr.send_command(command_json)
        print(f"Ответ: {response._content}\n")
        time.sleep(0.7)

        


if __name__ == "__main__":
    run_game_loop()
