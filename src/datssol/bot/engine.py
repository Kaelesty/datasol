"""Autonomous bot engine and planning primitives for Datssol."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from os import getpid
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable, Literal, Protocol

from datssol.data import GetArenaInteractor
from datssol.data import SubmitCommandInteractor
from datssol.model import ActionPath
from datssol.model import ArenaState
from datssol.model import Cell
from datssol.model import CommandRequest
from datssol.model import EnemyPlantation
from datssol.model import Plantation
from datssol.model import PlantationAction
from datssol.model import PlantationUpgrades
from datssol.model import Point
from datssol.model import RelocateMainPath


BotProfileName = Literal["safe", "expansion", "development", "aggressive"]
BotInteractorFactory = Callable[[str], tuple[GetArenaInteractor, SubmitCommandInteractor]]

DEFAULT_PROFILE: BotProfileName = "safe"
SUPPORTED_PROFILES: tuple[BotProfileName, ...] = ("safe", "expansion", "development", "aggressive")


@dataclass(slots=True, frozen=True)
class BotConfig:
    token_file: Path = Path(".token")
    timeout_seconds: float = 10.0
    poll_interval_seconds: float = 0.25
    log_dir: Path = Path("logs/bot-sessions")


@dataclass(slots=True, frozen=True)
class PlannedAction:
    kind: str
    summary: str
    score: float
    author: Point | None = None
    exit_point: Point | None = None
    target: Point | None = None


@dataclass(slots=True, frozen=True)
class DecisionAction:
    kind: str
    summary: str
    score: float
    author: Point | None = None
    exit_point: Point | None = None
    target: Point | None = None


@dataclass(slots=True, frozen=True)
class PlannedTurn:
    request: CommandRequest | None
    actions: tuple[PlannedAction, ...] = ()
    reason: str = ""
    estimated_score: float = 0.0
    diagnostics: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class DecisionSummary:
    turn_no: int | None = None
    profile: BotProfileName = DEFAULT_PROFILE
    reason: str = ""
    estimated_score: float = 0.0
    actions: tuple[str, ...] = ()
    action_details: tuple[DecisionAction, ...] = ()


@dataclass(slots=True, frozen=True)
class BotRuntimeState:
    running: bool = False
    server: str = "test"
    profile: BotProfileName = DEFAULT_PROFILE
    prod_guard_required: bool = False
    session_log_path: str | None = None
    last_seen_turn: int | None = None
    last_submitted_turn: int | None = None
    submitted_count: int = 0
    skipped_count: int = 0
    rejected_count: int = 0
    error_count: int = 0
    last_error: str | None = None
    last_decision: DecisionSummary | None = None


class BotStrategy(Protocol):
    """Score candidate actions and choose upgrades for a profile."""

    name: BotProfileName

    def score_build(self, *, remaining_percent: float, boosted: bool, frontier: int, contested: bool) -> float:
        """Return build desirability."""

    def score_repair(self, *, missing_hp: int, is_main: bool, is_critical: bool, target_hp: int) -> float:
        """Return repair desirability."""

    def score_sabotage(
        self,
        *,
        enemy_hp: int,
        boosted: bool,
        threatening_main: bool,
        contested: bool,
    ) -> float:
        """Return sabotage desirability."""

    def score_beaver(self, *, reward_points: int, turns_to_kill: int, contested: bool) -> float:
        """Return beaver-hunting desirability."""

    def choose_upgrade(self, safety: "BotSafetyValidator") -> str | None:
        """Pick an upgrade name or None."""

    def target_active_constructions(
        self,
        *,
        own_count: int,
        construction_count: int,
        connected_count: int,
        settlement_limit: int,
    ) -> int:
        """Return the preferred number of concurrent constructions."""

    def build_reserve_threshold(self) -> float:
        """Return the minimum non-build score needed to beat growth pressure."""

    def minimum_action_score(self, kind: str) -> float:
        """Return a per-action acceptance floor."""


@dataclass(slots=True, frozen=True)
class CandidateAction:
    kind: str
    author: Point
    exit_point: Point
    target: Point
    base_score: float
    base_power: int
    summary: str
    creates_new_construction: bool = True


class SessionLogger:
    """Session-scoped bot logger with one file per autonomous run."""

    def __init__(self, log_dir: Path, *, server: str, profile: BotProfileName) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        self.path = log_dir / f"bot-session-{timestamp}-{server}-{profile}-pid{getpid()}.log"
        self._handle = self.path.open("a", encoding="utf-8")
        self._lock = Lock()

    def write(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._handle.write(f"[{timestamp}] {message}\n")
            self._handle.flush()

    def close(self) -> None:
        with self._lock:
            if self._handle.closed:
                return
            self._handle.flush()
            self._handle.close()


class ProfileStrategy:
    def __init__(self, name: BotProfileName) -> None:
        if name not in SUPPORTED_PROFILES:
            raise ValueError(f"Unsupported bot profile: {name!r}")
        self.name = name

    def score_build(self, *, remaining_percent: float, boosted: bool, frontier: int, contested: bool) -> float:
        base = 78.0 + remaining_percent * 3.1 + frontier * 13.0
        if frontier >= 3:
            base += 18.0
        elif frontier == 2:
            base += 8.0
        if boosted:
            base += 125.0
        if contested:
            if self.name == "aggressive":
                base += 20.0
            elif self.name == "development":
                base -= 14.0
            else:
                base -= 8.0
        factors = {"safe": 1.32, "expansion": 1.58, "development": 1.82, "aggressive": 1.18}
        return base * factors[self.name]

    def score_repair(self, *, missing_hp: int, is_main: bool, is_critical: bool, target_hp: int) -> float:
        base = missing_hp * 3.2
        if is_main:
            base += 150.0
        if is_critical:
            base += 85.0
        if target_hp <= 20:
            base += 55.0
        factors = {"safe": 1.22, "expansion": 0.82, "development": 1.02, "aggressive": 0.74}
        return base * factors[self.name]

    def score_sabotage(
        self,
        *,
        enemy_hp: int,
        boosted: bool,
        threatening_main: bool,
        contested: bool,
    ) -> float:
        base = 78.0 + max(0.0, 60.0 - enemy_hp * 1.1)
        if boosted:
            base += 36.0
        if threatening_main:
            base += 60.0
        if contested:
            base += 24.0
        factors = {"safe": 0.34, "expansion": 0.22, "development": 0.1, "aggressive": 1.15}
        return base * factors[self.name]

    def score_beaver(self, *, reward_points: int, turns_to_kill: int, contested: bool) -> float:
        base = reward_points / max(1, turns_to_kill) / 55.0
        if contested:
            base -= 20.0 if self.name != "aggressive" else 6.0
        factors = {"safe": 0.74, "expansion": 0.54, "development": 0.28, "aggressive": 0.82}
        return base * factors[self.name]

    def target_active_constructions(
        self,
        *,
        own_count: int,
        construction_count: int,
        connected_count: int,
        settlement_limit: int,
    ) -> int:
        headroom = max(0, settlement_limit - own_count - construction_count)
        if headroom <= 0 or connected_count <= 0:
            return 0

        base_targets = {"safe": 2, "expansion": 3, "development": 4, "aggressive": 3}
        growth_bonus = max(0, min(2, connected_count // 3))
        target = base_targets[self.name] + growth_bonus
        return min(target, connected_count, construction_count + headroom)

    def build_reserve_threshold(self) -> float:
        thresholds = {"safe": 205.0, "expansion": 215.0, "development": 225.0, "aggressive": 235.0}
        return thresholds[self.name]

    def minimum_action_score(self, kind: str) -> float:
        if kind == "build":
            return 18.0
        floors = {"safe": 32.0, "expansion": 34.0, "development": 36.0, "aggressive": 32.0}
        return floors[self.name]

    def choose_upgrade(self, safety: "BotSafetyValidator") -> str | None:
        if not safety.has_upgrade_points:
            return None

        current_total = len(safety.arena.plantations) + len(safety.arena.construction)
        near_limit = current_total >= max(0, safety.settlement_limit - 2)
        orders: dict[BotProfileName, tuple[str, ...]] = {
            "safe": (
                "settlement_limit",
                "repair_power",
                "signal_range",
                "max_hp",
                "earthquake_mitigation",
                "beaver_damage_mitigation",
                "vision_range",
                "decay_mitigation",
            ),
            "expansion": (
                "settlement_limit",
                "repair_power",
                "signal_range",
                "max_hp",
                "vision_range",
                "decay_mitigation",
                "earthquake_mitigation",
                "beaver_damage_mitigation",
            ),
            "development": (
                "repair_power",
                "settlement_limit",
                "signal_range",
                "max_hp",
                "vision_range",
                "decay_mitigation",
                "earthquake_mitigation",
                "beaver_damage_mitigation",
            ),
            "aggressive": (
                "repair_power",
                "settlement_limit",
                "signal_range",
                "max_hp",
                "vision_range",
                "beaver_damage_mitigation",
                "earthquake_mitigation",
                "decay_mitigation",
            ),
        }

        if near_limit and safety.upgrade_is_available("settlement_limit"):
            return "settlement_limit"

        for tier_name in orders[self.name]:
            if safety.upgrade_is_available(tier_name):
                return tier_name
        return None


class BotSafetyValidator:
    """Rule-aware safety helper for planning and validation."""

    def __init__(self, arena: ArenaState) -> None:
        self.arena = arena
        self.own_by_pos = {item.position: item for item in arena.plantations}
        self.enemy_by_pos = {item.position: item for item in arena.enemy}
        self.beaver_by_pos = {item.position: item for item in arena.beavers}
        self.cell_by_pos = {item.position: item for item in arena.cells}
        self.construction_by_pos = {item.position: item for item in arena.construction}
        self.construction_positions = {item.position for item in arena.construction}
        self.mountains = set(arena.mountains)
        self.main = next((item for item in arena.plantations if item.is_main), None)
        self.connected_positions = self._compute_connected_positions()
        self.critical_positions = self._compute_critical_positions()
        upgrades = arena.plantation_upgrades
        self.tier_levels = {tier.name: tier.current for tier in upgrades.tiers} if upgrades else {}
        self.tier_max = {tier.name: tier.max for tier in upgrades.tiers} if upgrades else {}
        self.has_upgrade_points = bool(upgrades and upgrades.points > 0)
        self.signal_range = 3 + self.tier_levels.get("signal_range", 0)
        self.action_range = arena.action_range
        self.build_power = 5 + self.tier_levels.get("repair_power", 0)
        self.repair_power = 5 + self.tier_levels.get("repair_power", 0)
        self.sabotage_power = 5
        self.beaver_power = 5
        self.max_hp = 50 + self.tier_levels.get("max_hp", 0) * 10
        self.settlement_limit = 30 + self.tier_levels.get("settlement_limit", 0)

    def can_command(self, position: Point) -> bool:
        plantation = self.own_by_pos.get(position)
        return plantation is not None and not plantation.is_isolated and position in self.connected_positions

    def is_occupied(self, position: Point) -> bool:
        return (
            position in self.own_by_pos
            or position in self.enemy_by_pos
            or position in self.beaver_by_pos
            or position in self.construction_positions
        )

    def in_bounds(self, position: Point) -> bool:
        return 0 <= position.x < self.arena.size.width and 0 <= position.y < self.arena.size.height

    @staticmethod
    def in_square_range(origin: Point, target: Point, radius: int) -> bool:
        return abs(origin.x - target.x) <= radius and abs(origin.y - target.y) <= radius

    @staticmethod
    def is_boosted(position: Point) -> bool:
        return position.x % 7 == 0 and position.y % 7 == 0

    @staticmethod
    def is_orthogonally_adjacent(a: Point, b: Point) -> bool:
        return abs(a.x - b.x) + abs(a.y - b.y) == 1

    def is_safe_build_target(self, position: Point) -> bool:
        if not self.in_bounds(position) or position in self.mountains or self.is_occupied(position):
            return False
        return any(self.is_orthogonally_adjacent(position, candidate) for candidate in self.connected_positions)

    def cell_progress(self, position: Point) -> float:
        cell = self.cell_by_pos.get(position)
        return cell.terraformation_progress if cell is not None else 0.0

    def remaining_cell_value(self, position: Point) -> float:
        max_points = 1500.0 if self.is_boosted(position) else 1000.0
        remaining = max(0.0, 100.0 - self.cell_progress(position))
        return max_points * (remaining / 100.0)

    def upgrade_is_available(self, tier_name: str) -> bool:
        current = self.tier_levels.get(tier_name)
        maximum = self.tier_max.get(tier_name)
        return current is not None and maximum is not None and current < maximum

    def is_target_immune(self, enemy: EnemyPlantation | None) -> bool:
        return enemy is not None and enemy.immunity_until_turn is not None and enemy.immunity_until_turn > self.arena.turn_no

    def build_would_exceed_limit(self, extra_builds: int) -> bool:
        return len(self.arena.plantations) + len(self.arena.construction) + extra_builds > self.settlement_limit

    def construction_progress(self, position: Point) -> float:
        construction = self.construction_by_pos.get(position)
        return construction.progress if construction is not None else 0.0

    def adjacent_relocate_options(self) -> tuple[Plantation, ...]:
        if self.main is None:
            return ()
        return tuple(
            plantation
            for plantation in self.arena.plantations
            if plantation.position != self.main.position
            and self.can_command(plantation.position)
            and self.is_orthogonally_adjacent(plantation.position, self.main.position)
        )

    def choose_best_relocate_option(self, positions: tuple[Point, ...]) -> Point | None:
        if not positions:
            return None
        scored = []
        for position in positions:
            plantation = self.own_by_pos.get(position)
            scored.append(
                (
                    plantation.hp if plantation is not None else self.max_hp,
                    0 if position in self.critical_positions else 1,
                    int(self.is_boosted(position)),
                    -self.cell_progress(position),
                    position,
                )
            )
        return max(scored)[-1]

    def should_relocate_main(self) -> tuple[bool, Point | None]:
        if self.main is None:
            return False, None

        options = self.adjacent_relocate_options()
        if not options:
            return False, None

        # Move the CU as soon as a safe adjacent plantation exists.
        best = self.choose_best_relocate_option(tuple(item.position for item in options))
        return best is not None, best

    def validate_candidate(
        self,
        candidate: CandidateAction,
        *,
        exit_usage: Counter[Point],
        selected_authors: set[Point],
        selected_targets: set[Point],
        selected_builds: int,
    ) -> tuple[bool, str]:
        if candidate.author in selected_authors:
            return False, "author already used"
        if candidate.target in selected_targets and candidate.kind != "build":
            return False, "target already used"
        if not self.can_command(candidate.author):
            return False, "author is not connected to CU"
        if not self.can_command(candidate.exit_point):
            return False, "exit plantation is not connected to CU"
        if not self.in_square_range(candidate.author, candidate.exit_point, self.signal_range):
            return False, "exit point is out of signal range"
        if not self.in_square_range(candidate.exit_point, candidate.target, self.action_range):
            return False, "target is out of action range"
        if max(0, candidate.base_power - exit_usage[candidate.exit_point]) <= 0:
            return False, "routing penalty reduces action power to zero"
        if candidate.kind == "build":
            if candidate.creates_new_construction:
                if not self.is_safe_build_target(candidate.target):
                    return False, "unsafe build target"
                if self.build_would_exceed_limit(selected_builds + 1):
                    return False, "build would exceed settlement limit"
            elif candidate.target not in self.construction_positions:
                return False, "construction target is no longer visible"
        if candidate.kind == "repair":
            if candidate.target == candidate.author:
                return False, "plantation cannot repair itself"
            target = self.own_by_pos.get(candidate.target)
            if target is None or target.hp >= self.max_hp:
                return False, "repair target does not need repair"
        if candidate.kind == "sabotage":
            target = self.enemy_by_pos.get(candidate.target)
            if target is None:
                return False, "enemy target is no longer visible"
            if self.is_target_immune(target):
                return False, "enemy target is immune"
        if candidate.kind == "beaver" and candidate.target not in self.beaver_by_pos:
            return False, "beaver target is no longer visible"
        return True, ""

    def _compute_connected_positions(self) -> set[Point]:
        main = next((item for item in self.arena.plantations if item.is_main), None)
        if main is None:
            return set()

        queue = [main.position]
        visited = {main.position}
        while queue:
            current = queue.pop()
            for plantation in self.arena.plantations:
                if plantation.position in visited:
                    continue
                if plantation.is_isolated:
                    continue
                if self.is_orthogonally_adjacent(current, plantation.position):
                    visited.add(plantation.position)
                    queue.append(plantation.position)
        return visited

    def _compute_critical_positions(self) -> set[Point]:
        if self.main is None:
            return set()
        commandable = [position for position in self.connected_positions if self.can_command(position)]
        if not commandable:
            return {self.main.position}

        critical = {self.main.position}
        for position in commandable:
            if position == self.main.position:
                continue
            remaining = {item for item in commandable if item != position}
            if not remaining:
                critical.add(position)
                continue
            queue = [self.main.position]
            visited: set[Point] = set()
            while queue:
                current = queue.pop()
                if current == position or current not in remaining:
                    continue
                if current in visited:
                    continue
                visited.add(current)
                for candidate in remaining:
                    if candidate not in visited and self.is_orthogonally_adjacent(current, candidate):
                        queue.append(candidate)
            if visited != remaining:
                critical.add(position)
        return critical


class BotPlanner:
    """Build a safe, profile-aware command request from an arena snapshot."""

    def plan_turn(self, arena: ArenaState, profile: BotProfileName) -> PlannedTurn:
        safety = BotSafetyValidator(arena)
        strategy = ProfileStrategy(profile)
        candidate_actions = self._generate_candidates(arena, safety, strategy)
        selected_actions, selection_diagnostics = self._select_actions(candidate_actions, safety, strategy)
        diagnostics = self._build_diagnostics(arena, safety, candidate_actions, selected_actions, selection_diagnostics, profile)

        upgrade_name = strategy.choose_upgrade(safety)
        relocate_target = self._select_relocate_target(safety, selected_actions, profile)
        relocate_path = (
            RelocateMainPath(from_point=safety.main.position, to_point=relocate_target)
            if safety.main is not None and relocate_target is not None
            else None
        )

        command_actions = tuple(
            PlantationAction(
                path=ActionPath(
                    author=item.author,
                    exit_point=item.exit_point,
                    target=item.target,
                )
            )
            for item in selected_actions
        )
        request = CommandRequest(
            command=command_actions,
            plantation_upgrade=upgrade_name,
            relocate_main=relocate_path,
        )

        planned_actions = [
            PlannedAction(
                kind=item.kind,
                summary=item.summary,
                score=item.base_score,
                author=item.author,
                exit_point=item.exit_point,
                target=item.target,
            )
            for item in selected_actions
        ]

        reason_parts: list[str] = []
        if selected_actions:
            reason_parts.append(f"selected {len(selected_actions)} plantation actions")
        else:
            reason_parts.append("no safe plantation action found")
        if upgrade_name:
            reason_parts.append(f"upgrade={upgrade_name}")
            diagnostics.append(f"upgrade selected: {upgrade_name}")
            planned_actions.append(
                PlannedAction(kind="upgrade", summary=f"buy upgrade {upgrade_name}", score=32.0)
            )
        if relocate_path is not None:
            reason_parts.append(f"relocate main to [{relocate_target.x}, {relocate_target.y}]")
            diagnostics.append(f"relocate main selected: [{relocate_target.x}, {relocate_target.y}]")
            planned_actions.append(
                PlannedAction(
                    kind="relocate_main",
                    summary=f"relocate main to [{relocate_target.x}, {relocate_target.y}]",
                    score=220.0,
                    author=safety.main.position,
                    target=relocate_target,
                )
            )

        if not request.has_useful_action():
            return PlannedTurn(
                request=None,
                actions=tuple(planned_actions),
                reason="; ".join(reason_parts),
                estimated_score=0.0,
                diagnostics=tuple(diagnostics),
            )

        estimated_score = sum(item.score for item in planned_actions)
        return PlannedTurn(
            request=request,
            actions=tuple(planned_actions),
            reason="; ".join(reason_parts),
            estimated_score=estimated_score,
            diagnostics=tuple(diagnostics),
        )

    def _generate_candidates(
        self,
        arena: ArenaState,
        safety: BotSafetyValidator,
        strategy: BotStrategy,
    ) -> list[CandidateAction]:
        candidates: list[CandidateAction] = []
        connected_authors = [position for position in safety.connected_positions if safety.can_command(position)]
        if not connected_authors:
            return candidates

        desired_constructions = strategy.target_active_constructions(
            own_count=len(arena.plantations),
            construction_count=len(arena.construction),
            connected_count=len(connected_authors),
            settlement_limit=safety.settlement_limit,
        )
        construction_deficit = max(0, desired_constructions - len(arena.construction))
        contested_positions = {enemy.position for enemy in arena.enemy}
        for author in connected_authors:
            for exit_point in connected_authors:
                if not safety.in_square_range(author, exit_point, safety.signal_range):
                    continue
                for target in iter_square_positions(exit_point, safety.action_range, arena):
                    if target in safety.mountains:
                        continue
                    own_target = safety.own_by_pos.get(target)
                    enemy_target = safety.enemy_by_pos.get(target)
                    beaver_target = safety.beaver_by_pos.get(target)
                    construction_visible = target in safety.construction_positions
                    boosted = safety.is_boosted(target)
                    contested = target in contested_positions

                    if own_target is not None and target != author:
                        missing_hp = max(0, safety.max_hp - own_target.hp)
                        if missing_hp > 0:
                            score = strategy.score_repair(
                                missing_hp=missing_hp,
                                is_main=own_target.is_main,
                                is_critical=target in safety.critical_positions,
                                target_hp=own_target.hp,
                            )
                            candidates.append(
                                CandidateAction(
                                    kind="repair",
                                    author=author,
                                    exit_point=exit_point,
                                    target=target,
                                    base_score=score,
                                    base_power=safety.repair_power,
                                    summary=f"repair [{target.x}, {target.y}] from [{exit_point.x}, {exit_point.y}]",
                                )
                            )
                        continue

                    if enemy_target is not None and not construction_visible:
                        score = strategy.score_sabotage(
                            enemy_hp=enemy_target.hp,
                            boosted=boosted,
                            threatening_main=bool(
                                safety.main and manhattan_distance(enemy_target.position, safety.main.position) <= 2
                            ),
                            contested=contested,
                        )
                        candidates.append(
                            CandidateAction(
                                kind="sabotage",
                                author=author,
                                exit_point=exit_point,
                                target=target,
                                base_score=score,
                                base_power=safety.sabotage_power,
                                summary=f"sabotage [{target.x}, {target.y}] from [{exit_point.x}, {exit_point.y}]",
                            )
                        )
                        continue

                    if beaver_target is not None:
                        reward = 30000 if boosted else 20000
                        turns_to_kill = ceil(beaver_target.hp / max(1, safety.beaver_power))
                        score = strategy.score_beaver(
                            reward_points=reward,
                            turns_to_kill=turns_to_kill,
                            contested=contested,
                        )
                        candidates.append(
                            CandidateAction(
                                kind="beaver",
                                author=author,
                                exit_point=exit_point,
                                target=target,
                                base_score=score,
                                base_power=safety.beaver_power,
                                summary=f"attack beaver [{target.x}, {target.y}] from [{exit_point.x}, {exit_point.y}]",
                            )
                        )
                        continue

                    if construction_visible:
                        construction_progress = safety.construction_progress(target)
                        remaining_percent = max(0.0, 100.0 - safety.cell_progress(target))
                        frontier = sum(
                            1
                            for neighbor in orthogonal_neighbors(target, arena)
                            if neighbor not in safety.mountains
                            and neighbor not in safety.enemy_by_pos
                            and neighbor not in safety.beaver_by_pos
                        )
                        score = (
                            strategy.score_build(
                                remaining_percent=remaining_percent,
                                boosted=boosted,
                                frontier=frontier,
                                contested=contested,
                            )
                            + 320.0
                            + construction_progress * 5.5
                            + construction_deficit * 24.0
                        )
                        candidates.append(
                            CandidateAction(
                                kind="build",
                                author=author,
                                exit_point=exit_point,
                                target=target,
                                base_score=score,
                                base_power=safety.build_power,
                                summary=(
                                    f"continue construction [{target.x}, {target.y}] "
                                    f"from [{exit_point.x}, {exit_point.y}]"
                                ),
                                creates_new_construction=False,
                            )
                        )
                        continue

                    if safety.is_occupied(target):
                        continue
                    if not safety.is_safe_build_target(target):
                        continue

                    remaining_percent = max(0.0, 100.0 - safety.cell_progress(target))
                    frontier = sum(
                        1
                        for neighbor in orthogonal_neighbors(target, arena)
                        if neighbor not in safety.mountains and not safety.is_occupied(neighbor)
                    )
                    score = strategy.score_build(
                        remaining_percent=remaining_percent,
                        boosted=boosted,
                        frontier=frontier,
                        contested=contested,
                    ) + construction_deficit * 62.0
                    candidates.append(
                        CandidateAction(
                            kind="build",
                            author=author,
                            exit_point=exit_point,
                            target=target,
                            base_score=score,
                            base_power=safety.build_power,
                            summary=f"build [{target.x}, {target.y}] from [{exit_point.x}, {exit_point.y}]",
                            creates_new_construction=True,
                        )
                    )
        return candidates

    def _select_actions(
        self,
        candidates: list[CandidateAction],
        safety: BotSafetyValidator,
        strategy: BotStrategy,
    ) -> tuple[tuple[CandidateAction, ...], tuple[str, ...]]:
        selected: list[CandidateAction] = []
        diagnostics: list[str] = []
        exit_usage: Counter[Point] = Counter()
        selected_authors: set[Point] = set()
        selected_targets: set[Point] = set()
        selected_new_build_targets: set[Point] = set()
        selected_builds = 0
        selected_build_actions = 0
        rejection_counts: Counter[str] = Counter()

        ordered_candidates = sorted(candidates, key=self._candidate_sort_key, reverse=True)
        build_quota = strategy.target_active_constructions(
            own_count=len(safety.arena.plantations),
            construction_count=len(safety.arena.construction),
            connected_count=len(safety.connected_positions),
            settlement_limit=safety.settlement_limit,
        )
        for index, candidate in enumerate(ordered_candidates):
            valid, reason = safety.validate_candidate(
                candidate,
                exit_usage=exit_usage,
                selected_authors=selected_authors,
                selected_targets=selected_targets,
                selected_builds=selected_builds,
            )
            if not valid:
                rejection_counts[reason] += 1
                if index < 40:
                    diagnostics.append(f"reject {self._describe_candidate(candidate)} reason={reason}")
                continue

            effective_power = max(0, candidate.base_power - exit_usage[candidate.exit_point])
            adjusted_score = candidate.base_score * (effective_power / max(1, candidate.base_power))
            if (
                candidate.kind in {"sabotage", "beaver"}
                and selected_build_actions < build_quota
                and adjusted_score < strategy.build_reserve_threshold()
            ):
                rejection_counts["reserved for build pressure"] += 1
                if index < 40:
                    diagnostics.append(
                        f"reject {self._describe_candidate(candidate)} reason=reserved for build pressure "
                        f"build_quota={build_quota} selected_build_actions={selected_build_actions}"
                    )
                continue

            minimum_score = strategy.minimum_action_score(candidate.kind)
            if adjusted_score < minimum_score:
                rejection_counts["adjusted score below threshold"] += 1
                if index < 40:
                    diagnostics.append(
                        f"reject {self._describe_candidate(candidate)} reason=adjusted score below threshold "
                        f"adjusted_score={adjusted_score:.2f} minimum_score={minimum_score:.2f}"
                    )
                continue

            accepted = CandidateAction(
                kind=candidate.kind,
                author=candidate.author,
                exit_point=candidate.exit_point,
                target=candidate.target,
                base_score=adjusted_score,
                base_power=effective_power,
                summary=candidate.summary,
                creates_new_construction=candidate.creates_new_construction,
            )
            selected.append(accepted)
            diagnostics.append(
                f"select {self._describe_candidate(accepted)} raw_score={candidate.base_score:.2f}"
            )
            selected_authors.add(candidate.author)
            if candidate.kind != "build":
                selected_targets.add(candidate.target)
            exit_usage[candidate.exit_point] += 1
            if candidate.kind == "build":
                selected_build_actions += 1
                if candidate.creates_new_construction and candidate.target not in selected_new_build_targets:
                    selected_new_build_targets.add(candidate.target)
                    selected_builds += 1
        if rejection_counts:
            diagnostics.append(
                "rejection summary: "
                + ", ".join(
                    f"{reason}={count}" for reason, count in rejection_counts.most_common()
                )
            )
        return tuple(selected), tuple(diagnostics)

    def _build_diagnostics(
        self,
        arena: ArenaState,
        safety: BotSafetyValidator,
        candidates: list[CandidateAction],
        selected_actions: tuple[CandidateAction, ...],
        selection_diagnostics: tuple[str, ...],
        profile: BotProfileName,
    ) -> list[str]:
        diagnostics = [
            f"turn={arena.turn_no} profile={profile}",
            (
                "arena counts: "
                f"own={len(arena.plantations)} enemy={len(arena.enemy)} construction={len(arena.construction)} "
                f"beavers={len(arena.beavers)} cells={len(arena.cells)} mountains={len(arena.mountains)}"
            ),
            (
                "safety snapshot: "
                f"connected={len(safety.connected_positions)} critical={len(safety.critical_positions)} "
                f"signal_range={safety.signal_range} action_range={safety.action_range} "
                f"settlement_limit={safety.settlement_limit} has_upgrade_points={safety.has_upgrade_points}"
            ),
        ]
        by_kind = Counter(item.kind for item in candidates)
        diagnostics.append(
            "candidate counts: " + ", ".join(f"{kind}={count}" for kind, count in sorted(by_kind.items()))
            if by_kind
            else "candidate counts: none"
        )
        ordered = sorted(candidates, key=self._candidate_sort_key, reverse=True)
        diagnostics.append("top candidates:")
        if not ordered:
            diagnostics.append("  none")
        else:
            for candidate in ordered[:15]:
                diagnostics.append(f"  {self._describe_candidate(candidate)}")
        diagnostics.extend(selection_diagnostics)
        if selected_actions:
            diagnostics.append(
                "selected summary: " + "; ".join(self._describe_candidate(item) for item in selected_actions)
            )
        else:
            diagnostics.append("selected summary: none")
        return diagnostics

    @staticmethod
    def _describe_candidate(candidate: CandidateAction) -> str:
        build_mode = ""
        if candidate.kind == "build":
            build_mode = " mode=new" if candidate.creates_new_construction else " mode=continue"
        return (
            f"{candidate.kind}{build_mode} score={candidate.base_score:.2f} power={candidate.base_power} "
            f"author=[{candidate.author.x},{candidate.author.y}] "
            f"exit=[{candidate.exit_point.x},{candidate.exit_point.y}] "
            f"target=[{candidate.target.x},{candidate.target.y}]"
        )

    @staticmethod
    def _candidate_sort_key(candidate: CandidateAction) -> tuple[int, float]:
        if candidate.kind == "build" and not candidate.creates_new_construction:
            return (1, candidate.base_score)
        return (0, candidate.base_score)

    def _select_relocate_target(
        self,
        safety: BotSafetyValidator,
        selected_actions: tuple[CandidateAction, ...],
        profile: BotProfileName,
    ) -> Point | None:
        if safety.main is None:
            return None

        main_progress = safety.cell_progress(safety.main.position)
        force_relocate = profile != "development" or main_progress >= 95.0 or safety.main.hp <= 20

        adjacent_ready = tuple(item.position for item in safety.adjacent_relocate_options())
        if adjacent_ready and force_relocate:
            return safety.choose_best_relocate_option(adjacent_ready)

        completing_targets = tuple(
            action.target
            for action in selected_actions
            if action.kind == "build"
            and not action.creates_new_construction
            and safety.is_orthogonally_adjacent(action.target, safety.main.position)
            and safety.construction_progress(action.target) + action.base_power >= 50
        )
        if completing_targets and force_relocate:
            return safety.choose_best_relocate_option(completing_targets)
        return None


class BotRunner:
    """Threaded autonomous runner that plans and submits one turn at a time."""

    def __init__(
        self,
        *,
        config: BotConfig,
        interactor_factory: BotInteractorFactory,
        planner: BotPlanner | None = None,
    ) -> None:
        self._config = config
        self._interactor_factory = interactor_factory
        self._planner = planner or BotPlanner()
        self._lock = Lock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._session_logger: SessionLogger | None = None
        self._state = BotRuntimeState()
        self._processed_turn: int | None = None

    def get_state(self) -> BotRuntimeState:
        with self._lock:
            return BotRuntimeState(
                running=self._state.running,
                server=self._state.server,
                profile=self._state.profile,
                prod_guard_required=self._state.prod_guard_required,
                session_log_path=self._state.session_log_path,
                last_seen_turn=self._state.last_seen_turn,
                last_submitted_turn=self._state.last_submitted_turn,
                submitted_count=self._state.submitted_count,
                skipped_count=self._state.skipped_count,
                rejected_count=self._state.rejected_count,
                error_count=self._state.error_count,
                last_error=self._state.last_error,
                last_decision=self._state.last_decision,
            )

    def start(
        self,
        *,
        server: str,
        profile: BotProfileName,
        allow_prod: bool = False,
    ) -> BotRuntimeState:
        profile = normalize_profile(profile)
        if server not in {"test", "prod"}:
            raise ValueError(f"Unsupported server: {server!r}")
        if server == "prod" and not allow_prod:
            raise ValueError("Starting the bot on prod requires explicit allowProd=true.")

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                if self._session_logger is not None:
                    self._session_logger.write(
                        "START ignored: session already running "
                        f"current_server={self._state.server} current_profile={self._state.profile} "
                        f"requested_server={server} requested_profile={profile}"
                    )
                return BotRuntimeState(
                    running=self._state.running,
                    server=self._state.server,
                    profile=self._state.profile,
                    prod_guard_required=self._state.prod_guard_required,
                    session_log_path=self._state.session_log_path,
                    last_seen_turn=self._state.last_seen_turn,
                    last_submitted_turn=self._state.last_submitted_turn,
                    submitted_count=self._state.submitted_count,
                    skipped_count=self._state.skipped_count,
                    rejected_count=self._state.rejected_count,
                    error_count=self._state.error_count,
                    last_error=self._state.last_error,
                    last_decision=self._state.last_decision,
                )
            self._processed_turn = None
            self._stop_event.clear()
            self._session_logger = SessionLogger(self._config.log_dir, server=server, profile=profile)
            self._session_logger.write(
                "SESSION START "
                f"server={server} profile={profile} "
                f"token_file={self._config.token_file} timeout_seconds={self._config.timeout_seconds} "
                f"poll_interval_seconds={self._config.poll_interval_seconds}"
            )
            self._state = BotRuntimeState(
                running=True,
                server=server,
                profile=profile,
                prod_guard_required=server == "prod",
                session_log_path=str(self._session_logger.path),
                last_seen_turn=self._state.last_seen_turn,
                last_submitted_turn=self._state.last_submitted_turn,
                submitted_count=self._state.submitted_count,
                skipped_count=self._state.skipped_count,
                rejected_count=self._state.rejected_count,
                error_count=self._state.error_count,
                last_error=None,
                last_decision=self._state.last_decision,
            )
            self._thread = Thread(target=self._run_loop, name="datssol-bot-runner", daemon=True)
            self._thread.start()
        return self.get_state()

    def stop(self) -> BotRuntimeState:
        thread: Thread | None = None
        with self._lock:
            self._state = BotRuntimeState(
                running=False,
                server=self._state.server,
                profile=self._state.profile,
                prod_guard_required=self._state.server == "prod",
                session_log_path=self._state.session_log_path,
                last_seen_turn=self._state.last_seen_turn,
                last_submitted_turn=self._state.last_submitted_turn,
                submitted_count=self._state.submitted_count,
                skipped_count=self._state.skipped_count,
                rejected_count=self._state.rejected_count,
                error_count=self._state.error_count,
                last_error=self._state.last_error,
                last_decision=self._state.last_decision,
            )
            self._stop_event.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=1.0)
        with self._lock:
            self._thread = None
        if self._session_logger is not None:
            self._session_logger.write("SESSION STOP")
            self._session_logger.close()
            self._session_logger = None
        return self.get_state()

    def set_profile(self, profile: BotProfileName) -> BotRuntimeState:
        profile = normalize_profile(profile)
        with self._lock:
            self._state = BotRuntimeState(
                running=self._state.running,
                server=self._state.server,
                profile=profile,
                prod_guard_required=self._state.server == "prod",
                session_log_path=self._state.session_log_path,
                last_seen_turn=self._state.last_seen_turn,
                last_submitted_turn=self._state.last_submitted_turn,
                submitted_count=self._state.submitted_count,
                skipped_count=self._state.skipped_count,
                rejected_count=self._state.rejected_count,
                error_count=self._state.error_count,
                last_error=self._state.last_error,
                last_decision=self._state.last_decision,
            )
        self._log(f"PROFILE UPDATE profile={profile}")
        return self.get_state()

    def set_server(self, server: str) -> BotRuntimeState:
        if server not in {"test", "prod"}:
            raise ValueError(f"Unsupported server: {server!r}")
        with self._lock:
            if self._state.running:
                raise ValueError("Stop the bot before changing its server.")
            self._state = BotRuntimeState(
                running=False,
                server=server,
                profile=self._state.profile,
                prod_guard_required=server == "prod",
                session_log_path=self._state.session_log_path,
                last_seen_turn=self._state.last_seen_turn,
                last_submitted_turn=self._state.last_submitted_turn,
                submitted_count=self._state.submitted_count,
                skipped_count=self._state.skipped_count,
                rejected_count=self._state.rejected_count,
                error_count=self._state.error_count,
                last_error=self._state.last_error,
                last_decision=self._state.last_decision,
            )
        self._log(f"SERVER UPDATE server={server}")
        return self.get_state()

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._config.poll_interval_seconds):
            state = self.get_state()
            if not state.running:
                return
            try:
                arena_interactor, command_interactor = self._interactor_factory(state.server)
                arena = arena_interactor.execute()
            except Exception as exc:  # pragma: no cover - exercised in tests via state assertions
                self._record_error(f"arena fetch failed: {exc}")
                continue

            with self._lock:
                self._state = BotRuntimeState(
                    running=self._state.running,
                    server=self._state.server,
                    profile=self._state.profile,
                    prod_guard_required=self._state.server == "prod",
                    session_log_path=self._state.session_log_path,
                    last_seen_turn=arena.turn_no,
                    last_submitted_turn=self._state.last_submitted_turn,
                    submitted_count=self._state.submitted_count,
                    skipped_count=self._state.skipped_count,
                    rejected_count=self._state.rejected_count,
                    error_count=self._state.error_count,
                    last_error=self._state.last_error,
                    last_decision=self._state.last_decision,
                )

            if self._processed_turn == arena.turn_no:
                continue

            self._log(_format_arena_snapshot(arena))
            planned_turn = self._planner.plan_turn(arena, state.profile)
            for line in planned_turn.diagnostics:
                self._log(f"PLAN {line}")
            self._record_decision(
                arena.turn_no,
                state.profile,
                reason=planned_turn.reason,
                estimated_score=planned_turn.estimated_score,
                actions=tuple(item.summary for item in planned_turn.actions),
                action_details=tuple(
                    DecisionAction(
                        kind=item.kind,
                        summary=item.summary,
                        score=item.score,
                        author=item.author,
                        exit_point=item.exit_point,
                        target=item.target,
                    )
                    for item in planned_turn.actions
                ),
            )

            request = planned_turn.request
            if request is None or not request.has_useful_action():
                self._processed_turn = arena.turn_no
                self._log(f"TURN {arena.turn_no} SKIP reason={planned_turn.reason}")
                with self._lock:
                    self._state = BotRuntimeState(
                        running=self._state.running,
                        server=self._state.server,
                        profile=self._state.profile,
                        prod_guard_required=self._state.server == "prod",
                        session_log_path=self._state.session_log_path,
                        last_seen_turn=self._state.last_seen_turn,
                        last_submitted_turn=self._state.last_submitted_turn,
                        submitted_count=self._state.submitted_count,
                        skipped_count=self._state.skipped_count + 1,
                        rejected_count=self._state.rejected_count,
                        error_count=self._state.error_count,
                        last_error=self._state.last_error,
                        last_decision=self._state.last_decision,
                    )
                continue

            self._log(f"TURN {arena.turn_no} REQUEST {_describe_command_request(request)}")
            try:
                response = command_interactor.execute(request)
            except Exception as exc:  # pragma: no cover - exercised in tests via state assertions
                self._record_error(f"command submit failed: {exc}")
                continue

            self._processed_turn = arena.turn_no
            if response.is_success:
                self._log(f"TURN {arena.turn_no} RESPONSE success code={response.code} errors=[]")
                with self._lock:
                    self._state = BotRuntimeState(
                        running=self._state.running,
                        server=self._state.server,
                        profile=self._state.profile,
                        prod_guard_required=self._state.server == "prod",
                        session_log_path=self._state.session_log_path,
                        last_seen_turn=self._state.last_seen_turn,
                        last_submitted_turn=arena.turn_no,
                        submitted_count=self._state.submitted_count + 1,
                        skipped_count=self._state.skipped_count,
                        rejected_count=self._state.rejected_count,
                        error_count=self._state.error_count,
                        last_error=None,
                        last_decision=self._state.last_decision,
                    )
                continue

            error_text = "; ".join(response.errors) if response.errors else "unknown command rejection"
            self._log(f"TURN {arena.turn_no} RESPONSE failure code={response.code} errors={error_text}")
            with self._lock:
                self._state = BotRuntimeState(
                    running=self._state.running,
                    server=self._state.server,
                    profile=self._state.profile,
                    prod_guard_required=self._state.server == "prod",
                    session_log_path=self._state.session_log_path,
                    last_seen_turn=self._state.last_seen_turn,
                    last_submitted_turn=arena.turn_no if "already submitted" in error_text else self._state.last_submitted_turn,
                    submitted_count=self._state.submitted_count,
                    skipped_count=self._state.skipped_count,
                    rejected_count=self._state.rejected_count + 1,
                    error_count=self._state.error_count + 1,
                    last_error=error_text,
                    last_decision=self._state.last_decision,
                )

    def _record_error(self, message: str) -> None:
        with self._lock:
            self._state = BotRuntimeState(
                running=self._state.running,
                server=self._state.server,
                profile=self._state.profile,
                prod_guard_required=self._state.server == "prod",
                session_log_path=self._state.session_log_path,
                last_seen_turn=self._state.last_seen_turn,
                last_submitted_turn=self._state.last_submitted_turn,
                submitted_count=self._state.submitted_count,
                skipped_count=self._state.skipped_count,
                rejected_count=self._state.rejected_count,
                error_count=self._state.error_count + 1,
                last_error=message,
                last_decision=self._state.last_decision,
            )
        self._log(f"ERROR {message}")

    def _record_decision(
        self,
        turn_no: int,
        profile: BotProfileName,
        *,
        reason: str,
        estimated_score: float,
        actions: tuple[str, ...],
        action_details: tuple[DecisionAction, ...],
    ) -> None:
        decision = DecisionSummary(
            turn_no=turn_no,
            profile=profile,
            reason=reason,
            estimated_score=round(estimated_score, 2),
            actions=actions,
            action_details=action_details,
        )
        with self._lock:
            self._state = BotRuntimeState(
                running=self._state.running,
                server=self._state.server,
                profile=self._state.profile,
                prod_guard_required=self._state.server == "prod",
                session_log_path=self._state.session_log_path,
                last_seen_turn=self._state.last_seen_turn,
                last_submitted_turn=self._state.last_submitted_turn,
                submitted_count=self._state.submitted_count,
                skipped_count=self._state.skipped_count,
                rejected_count=self._state.rejected_count,
                error_count=self._state.error_count,
                last_error=self._state.last_error,
                last_decision=decision,
            )
        self._log(
            f"DECISION turn={turn_no} profile={profile} estimated_score={decision.estimated_score} "
            f"reason={reason} actions={list(actions)}"
        )

    def _log(self, message: str) -> None:
        logger = self._session_logger
        if logger is None:
            return
        logger.write(message)


def normalize_profile(profile: str | None) -> BotProfileName:
    if profile is None:
        return DEFAULT_PROFILE
    lowered = profile.strip().lower()
    if lowered not in SUPPORTED_PROFILES:
        raise ValueError(f"Unsupported bot profile: {profile!r}")
    return lowered  # type: ignore[return-value]


def iter_square_positions(origin: Point, radius: int, arena: ArenaState) -> tuple[Point, ...]:
    points: list[Point] = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            target = Point(origin.x + dx, origin.y + dy)
            if 0 <= target.x < arena.size.width and 0 <= target.y < arena.size.height:
                points.append(target)
    return tuple(points)


def orthogonal_neighbors(origin: Point, arena: ArenaState) -> tuple[Point, ...]:
    candidates = (
        Point(origin.x - 1, origin.y),
        Point(origin.x + 1, origin.y),
        Point(origin.x, origin.y - 1),
        Point(origin.x, origin.y + 1),
    )
    return tuple(
        point
        for point in candidates
        if 0 <= point.x < arena.size.width and 0 <= point.y < arena.size.height
    )


def manhattan_distance(a: Point, b: Point) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)


def _describe_command_request(request: CommandRequest) -> str:
    command_parts = [
        (
            f"path=[[{action.path.author.x},{action.path.author.y}],"
            f"[{action.path.exit_point.x},{action.path.exit_point.y}],"
            f"[{action.path.target.x},{action.path.target.y}]]"
        )
        for action in request.command
    ]
    relocate = None
    if request.relocate_main is not None:
        relocate = (
            f"[[{request.relocate_main.from_point.x},{request.relocate_main.from_point.y}],"
            f"[{request.relocate_main.to_point.x},{request.relocate_main.to_point.y}]]"
        )
    return (
        f"commands={command_parts or []} "
        f"plantation_upgrade={request.plantation_upgrade!r} "
        f"relocate_main={relocate!r}"
    )


def _format_arena_snapshot(arena: ArenaState) -> str:
    main = next((item for item in arena.plantations if item.is_main), None)
    upgrades = arena.plantation_upgrades
    return (
        f"TURN {arena.turn_no} SNAPSHOT "
        f"next_turn_in={arena.next_turn_in:.3f}s "
        f"map={arena.size.width}x{arena.size.height} "
        f"own={len(arena.plantations)} enemy={len(arena.enemy)} construction={len(arena.construction)} "
        f"beavers={len(arena.beavers)} cells={len(arena.cells)} "
        f"main={f'[{main.position.x},{main.position.y}] hp={main.hp} isolated={main.is_isolated}' if main else 'none'} "
        f"upgrade_points={upgrades.points if upgrades else 0}"
    )
