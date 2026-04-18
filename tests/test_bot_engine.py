import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datssol.bot import BotConfig
from datssol.bot import BotPlanner
from datssol.bot import BotRunner
from datssol.bot import BotSafetyValidator
from datssol.bot.engine import PlannedAction
from datssol.bot.engine import PlannedTurn
from datssol.model import ArenaState
from datssol.model import Cell
from datssol.model import CommandRequest
from datssol.model import CommandResponse
from datssol.model import Construction
from datssol.model import EnemyPlantation
from datssol.model import MapSize
from datssol.model import Plantation
from datssol.model import PlantationAction
from datssol.model import PlantationUpgrades
from datssol.model import Point
from datssol.model import UpgradeTier


def make_arena(
    *,
    turn_no: int = 10,
    plantations: tuple[Plantation, ...],
    enemy: tuple[EnemyPlantation, ...] = (),
    cells: tuple[Cell, ...] = (),
    construction_positions: tuple[Point, ...] = (),
    construction_specs: tuple[tuple[Point, float], ...] = (),
    beavers=(),
    mountains=(),
    action_range: int = 2,
    size: tuple[int, int] = (12, 12),
    upgrades: PlantationUpgrades | None = None,
) -> ArenaState:
    constructions = [Construction(position=point, progress=10.0) for point in construction_positions]
    constructions.extend(Construction(position=point, progress=progress) for point, progress in construction_specs)
    return ArenaState(
        turn_no=turn_no,
        next_turn_in=0.6,
        size=MapSize(*size),
        action_range=action_range,
        plantations=plantations,
        enemy=enemy,
        mountains=tuple(mountains),
        cells=cells,
        construction=tuple(constructions),
        beavers=tuple(beavers),
        plantation_upgrades=upgrades,
        meteo_forecasts=(),
    )


def make_upgrades(**levels: int) -> PlantationUpgrades:
    defaults = {
        "repair_power": (0, 3),
        "max_hp": (0, 5),
        "settlement_limit": (0, 10),
        "signal_range": (0, 5),
        "decay_mitigation": (0, 3),
        "earthquake_mitigation": (0, 3),
        "beaver_damage_mitigation": (0, 5),
        "vision_range": (0, 5),
    }
    tiers = tuple(
        UpgradeTier(name=name, current=levels.get(name, current), max=maximum)
        for name, (current, maximum) in defaults.items()
    )
    points = 1 if levels.get("points", 0) else 0
    return PlantationUpgrades(
        points=points,
        interval_turns=30,
        turns_until_points=4,
        max_points=15,
        tiers=tiers,
    )


class BotSafetyTests(unittest.TestCase):
    def test_connectivity_is_orthogonal_only(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(1, 1), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="line", position=Point(1, 2), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="diag", position=Point(2, 3), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            )
        )
        safety = BotSafetyValidator(arena)
        self.assertIn(Point(1, 2), safety.connected_positions)
        self.assertNotIn(Point(2, 3), safety.connected_positions)

    def test_safe_validator_blocks_build_over_limit(self) -> None:
        plantations = tuple(
            Plantation(
                id=f"p{index}",
                position=Point(index, 0),
                is_main=index == 0,
                is_isolated=False,
                immunity_until_turn=None,
                hp=50,
            )
            for index in range(30)
        )
        arena = make_arena(plantations=plantations)
        safety = BotSafetyValidator(arena)
        self.assertTrue(safety.build_would_exceed_limit(1))


class PlannerProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = BotPlanner()

    def test_safe_profile_prefers_build_over_risky_sabotage(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(2, 2), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="ally", position=Point(2, 3), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            enemy=(EnemyPlantation(id="enemy", position=Point(4, 2), hp=8),),
            cells=(Cell(position=Point(3, 3), terraformation_progress=95.0, turns_until_degradation=8),),
        )
        planned = self.planner.plan_turn(arena, "safe")
        self.assertTrue(planned.actions)
        self.assertEqual(planned.actions[0].kind, "build")

    def test_expansion_prefers_boosted_build_target(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(7, 6), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="ally", position=Point(7, 5), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            cells=(Cell(position=Point(8, 6), terraformation_progress=0.0, turns_until_degradation=None),),
        )
        planned = self.planner.plan_turn(arena, "expansion")
        build_actions = [action for action in planned.actions if action.kind == "build"]
        self.assertTrue(build_actions)
        self.assertEqual(build_actions[0].target, Point(7, 7))

    def test_development_profile_keeps_focus_on_base_growth_without_early_relocate(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(7, 6), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="ally", position=Point(7, 7), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            cells=(Cell(position=Point(8, 6), terraformation_progress=0.0, turns_until_degradation=None),),
        )
        planned = self.planner.plan_turn(arena, "development")
        build_actions = [action for action in planned.actions if action.kind == "build"]
        self.assertTrue(build_actions)
        self.assertIsNotNone(planned.request)
        self.assertIsNone(planned.request.relocate_main)

    def test_development_profile_uses_emergency_relocate_when_main_cell_is_near_completion(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(4, 4), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="ally", position=Point(4, 5), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            cells=(Cell(position=Point(4, 4), terraformation_progress=96.0, turns_until_degradation=None),),
        )
        planned = self.planner.plan_turn(arena, "development")
        self.assertIsNotNone(planned.request)
        self.assertIsNotNone(planned.request.relocate_main)
        self.assertEqual(planned.request.relocate_main.to_point, Point(4, 5))

    def test_aggressive_prefers_sabotage_when_build_value_is_poor(self) -> None:
        allowed_positions = {Point(2, 2), Point(2, 3), Point(4, 2), Point(3, 3)}
        mountains = tuple(
            Point(x, y)
            for x in range(6)
            for y in range(6)
            if Point(x, y) not in allowed_positions
        )
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(2, 2), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="ally", position=Point(2, 3), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            enemy=(EnemyPlantation(id="enemy", position=Point(4, 2), hp=1),),
            cells=(Cell(position=Point(3, 3), terraformation_progress=95.0, turns_until_degradation=8),),
            mountains=mountains,
            size=(6, 6),
        )
        planned = self.planner.plan_turn(arena, "aggressive")
        self.assertTrue(planned.actions)
        self.assertEqual(planned.actions[0].kind, "sabotage")

    def test_planner_avoids_sabotage_on_visible_construction_cell(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(2, 2), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="ally", position=Point(2, 3), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            construction_positions=(Point(4, 2),),
        )
        planned = self.planner.plan_turn(arena, "aggressive")
        self.assertFalse(any(action.kind == "sabotage" for action in planned.actions))

    def test_planner_prefers_continuing_existing_construction(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(5, 5), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            construction_specs=((Point(5, 4), 25.0),),
            cells=(Cell(position=Point(5, 4), terraformation_progress=0.0, turns_until_degradation=None),),
        )
        planned = self.planner.plan_turn(arena, "safe")
        build_actions = [action for action in planned.actions if action.kind == "build"]
        self.assertTrue(build_actions)
        self.assertEqual(build_actions[0].target, Point(5, 4))
        self.assertIn("continue construction", build_actions[0].summary)

    def test_planner_relocates_main_to_adjacent_finished_plantation(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(3, 3), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="ally", position=Point(3, 4), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
        )
        planned = self.planner.plan_turn(arena, "safe")
        self.assertIsNotNone(planned.request)
        self.assertIsNotNone(planned.request.relocate_main)
        self.assertEqual(planned.request.relocate_main.to_point, Point(3, 4))

    def test_planner_relocates_main_when_adjacent_construction_completes_this_turn(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(4, 4), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            construction_specs=((Point(4, 5), 45.0),),
            cells=(Cell(position=Point(4, 5), terraformation_progress=0.0, turns_until_degradation=None),),
        )
        planned = self.planner.plan_turn(arena, "safe")
        self.assertIsNotNone(planned.request)
        self.assertIsNotNone(planned.request.relocate_main)
        self.assertEqual(planned.request.relocate_main.to_point, Point(4, 5))
        self.assertTrue(any(action.target == Point(4, 5) for action in planned.actions if action.kind == "build"))

    def test_planner_allows_multiple_authors_to_continue_same_construction(self) -> None:
        arena = make_arena(
            plantations=(
                Plantation(id="main", position=Point(5, 5), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),
                Plantation(id="ally", position=Point(5, 6), is_main=False, is_isolated=False, immunity_until_turn=None, hp=50),
            ),
            construction_specs=((Point(5, 4), 20.0),),
            cells=(Cell(position=Point(5, 4), terraformation_progress=0.0, turns_until_degradation=None),),
        )
        planned = self.planner.plan_turn(arena, "safe")
        build_actions = [action for action in planned.actions if action.kind == "build" and action.target == Point(5, 4)]
        self.assertGreaterEqual(len(build_actions), 2)


class FakeArenaInteractor:
    def __init__(self, arena: ArenaState) -> None:
        self.arena = arena

    def execute(self) -> ArenaState:
        return self.arena


class FakeCommandInteractor:
    def __init__(self, response: CommandResponse) -> None:
        self.response = response
        self.calls: list[CommandRequest] = []

    def execute(self, request: CommandRequest) -> CommandResponse:
        self.calls.append(request)
        return self.response


class StaticPlanner:
    def __init__(self, request: CommandRequest, diagnostics: tuple[str, ...] = ()) -> None:
        self.request = request
        self.diagnostics = diagnostics

    def plan_turn(self, arena: ArenaState, profile: str) -> PlannedTurn:
        return PlannedTurn(
            request=self.request,
            actions=(PlannedAction(kind="upgrade", summary="buy upgrade repair_power", score=10.0),),
            reason="static request",
            estimated_score=10.0,
            diagnostics=self.diagnostics,
        )


class RunnerTests(unittest.TestCase):
    def test_runner_submits_at_most_once_per_turn(self) -> None:
        arena = make_arena(
            plantations=(Plantation(id="main", position=Point(1, 1), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),),
        )
        command_interactor = FakeCommandInteractor(CommandResponse(code=0, errors=()))
        runner = BotRunner(
            config=BotConfig(timeout_seconds=1.0, poll_interval_seconds=0.01),
            interactor_factory=lambda server: (FakeArenaInteractor(arena), command_interactor),
            planner=StaticPlanner(CommandRequest(plantation_upgrade="repair_power")),
        )
        runner.start(server="test", profile="safe")
        time.sleep(0.08)
        runner.stop()
        self.assertEqual(len(command_interactor.calls), 1)
        self.assertEqual(runner.get_state().submitted_count, 1)

    def test_runner_marks_already_submitted_turn_as_processed(self) -> None:
        arena = make_arena(
            plantations=(Plantation(id="main", position=Point(1, 1), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),),
        )
        command_interactor = FakeCommandInteractor(
            CommandResponse(code=0, errors=("command already submitted this turn",))
        )
        runner = BotRunner(
            config=BotConfig(timeout_seconds=1.0, poll_interval_seconds=0.01),
            interactor_factory=lambda server: (FakeArenaInteractor(arena), command_interactor),
            planner=StaticPlanner(CommandRequest(plantation_upgrade="repair_power")),
        )
        runner.start(server="test", profile="safe")
        time.sleep(0.08)
        runner.stop()
        state = runner.get_state()
        self.assertEqual(len(command_interactor.calls), 1)
        self.assertEqual(state.last_submitted_turn, arena.turn_no)
        self.assertEqual(state.rejected_count, 1)

    def test_runner_writes_separate_session_logs_with_decision_context(self) -> None:
        arena_one = make_arena(
            turn_no=10,
            plantations=(Plantation(id="main", position=Point(1, 1), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),),
        )
        arena_two = make_arena(
            turn_no=11,
            plantations=(Plantation(id="main", position=Point(2, 2), is_main=True, is_isolated=False, immunity_until_turn=None, hp=50),),
        )
        current = {
            "arena": arena_one,
            "command_interactor": FakeCommandInteractor(CommandResponse(code=0, errors=())),
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = BotRunner(
                config=BotConfig(
                    timeout_seconds=1.0,
                    poll_interval_seconds=0.01,
                    log_dir=Path(tmpdir),
                ),
                interactor_factory=lambda server: (
                    FakeArenaInteractor(current["arena"]),
                    current["command_interactor"],
                ),
                planner=StaticPlanner(
                    CommandRequest(plantation_upgrade="repair_power"),
                    diagnostics=("planner profile snapshot", "candidate counts: upgrade-only"),
                ),
            )

            runner.start(server="test", profile="safe")
            time.sleep(0.08)
            first_state = runner.stop()
            first_log = Path(first_state.session_log_path)

            current["arena"] = arena_two
            current["command_interactor"] = FakeCommandInteractor(CommandResponse(code=0, errors=()))

            runner.start(server="test", profile="aggressive")
            time.sleep(0.08)
            second_state = runner.stop()
            second_log = Path(second_state.session_log_path)

            self.assertNotEqual(first_log, second_log)
            self.assertEqual(len(list(Path(tmpdir).glob("*.log"))), 2)

            first_content = first_log.read_text(encoding="utf-8")
            self.assertIn("SESSION START server=test profile=safe", first_content)
            self.assertIn("TURN 10 SNAPSHOT", first_content)
            self.assertIn("PLAN planner profile snapshot", first_content)
            self.assertIn("PLAN candidate counts: upgrade-only", first_content)
            self.assertIn("DECISION turn=10 profile=safe", first_content)
            self.assertIn("TURN 10 REQUEST", first_content)
            self.assertIn("TURN 10 RESPONSE success", first_content)
            self.assertIn("SESSION STOP", first_content)

            second_content = second_log.read_text(encoding="utf-8")
            self.assertIn("SESSION START server=test profile=aggressive", second_content)
            self.assertIn("TURN 11 SNAPSHOT", second_content)
            self.assertIn("DECISION turn=11 profile=aggressive", second_content)
            self.assertIn("SESSION STOP", second_content)


if __name__ == "__main__":
    unittest.main()
