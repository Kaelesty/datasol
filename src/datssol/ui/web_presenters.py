"""Presentation helpers for the read-only web UI."""

from __future__ import annotations

from datssol.bot import BotRuntimeState
from datssol.model import ArenaState
from datssol.model import LogsResponse
from datssol.model import Plantation


def arena_to_payload(state: ArenaState) -> dict[str, object]:
    upgrades = state.plantation_upgrades
    return {
        "turnNo": state.turn_no,
        "nextTurnIn": round(state.next_turn_in, 3),
        "size": {"width": state.size.width, "height": state.size.height},
        "actionRange": state.action_range,
        "counts": {
            "own": len(state.plantations),
            "enemy": len(state.enemy),
            "cells": len(state.cells),
            "construction": len(state.construction),
            "beavers": len(state.beavers),
            "mountains": len(state.mountains),
            "meteo": len(state.meteo_forecasts),
        },
        "plantations": [plantation_to_payload(item) for item in state.plantations],
        "enemy": [
            {
                "id": item.id,
                "position": point_to_payload(item.position),
                "hp": item.hp,
                "immunityUntilTurn": item.immunity_until_turn,
            }
            for item in state.enemy
        ],
        "construction": [
            {
                "position": point_to_payload(item.position),
                "progress": item.progress,
            }
            for item in state.construction
        ],
        "beavers": [
            {
                "id": item.id,
                "position": point_to_payload(item.position),
                "hp": item.hp,
            }
            for item in state.beavers
        ],
        "mountains": [point_to_payload(item) for item in state.mountains],
        "cells": [
            {
                "position": point_to_payload(item.position),
                "terraformationProgress": item.terraformation_progress,
                "turnsUntilDegradation": item.turns_until_degradation,
            }
            for item in state.cells
        ],
        "meteoForecasts": [
            {
                "kind": item.kind,
                "turnsUntil": item.turns_until,
                "id": item.id,
                "forming": item.forming,
                "position": point_to_payload(item.position) if item.position else None,
                "nextPosition": point_to_payload(item.next_position) if item.next_position else None,
                "radius": item.radius,
            }
            for item in state.meteo_forecasts
        ],
        "upgrades": (
            {
                "points": upgrades.points,
                "intervalTurns": upgrades.interval_turns,
                "turnsUntilPoints": upgrades.turns_until_points,
                "maxPoints": upgrades.max_points,
                "tiers": [
                    {"name": tier.name, "current": tier.current, "max": tier.max}
                    for tier in upgrades.tiers
                ],
            }
            if upgrades is not None
            else None
        ),
    }


def logs_to_payload(response: LogsResponse, tail: int) -> dict[str, object]:
    if response.error is not None:
        return {
            "error": {
                "code": response.error.code,
                "statusCode": response.error.status_code,
                "errors": list(response.error.errors),
            },
            "entries": [],
            "totalEntries": 0,
            "tail": tail,
        }

    entries = response.entries[-tail:] if tail > 0 else response.entries
    return {
        "error": None,
        "entries": [{"time": item.time, "message": item.message} for item in entries],
        "totalEntries": len(response.entries),
        "tail": tail,
    }


def bot_state_to_payload(state: BotRuntimeState) -> dict[str, object]:
    decision = state.last_decision
    return {
        "running": state.running,
        "server": state.server,
        "profile": state.profile,
        "prodGuardRequired": state.prod_guard_required,
        "sessionLogPath": state.session_log_path,
        "lastSeenTurn": state.last_seen_turn,
        "lastSubmittedTurn": state.last_submitted_turn,
        "submittedCount": state.submitted_count,
        "skippedCount": state.skipped_count,
        "rejectedCount": state.rejected_count,
        "errorCount": state.error_count,
        "lastError": state.last_error,
        "lastDecision": (
            {
                "turnNo": decision.turn_no,
                "profile": decision.profile,
                "reason": decision.reason,
                "estimatedScore": decision.estimated_score,
                "actions": list(decision.actions),
                "actionDetails": [
                    {
                        "kind": item.kind,
                        "summary": item.summary,
                        "score": item.score,
                        "author": point_to_payload(item.author) if item.author else None,
                        "exitPoint": point_to_payload(item.exit_point) if item.exit_point else None,
                        "target": point_to_payload(item.target) if item.target else None,
                    }
                    for item in decision.action_details
                ],
            }
            if decision is not None
            else None
        ),
    }


def plantation_to_payload(plantation: Plantation) -> dict[str, object]:
    return {
        "id": plantation.id,
        "position": point_to_payload(plantation.position),
        "isMain": plantation.is_main,
        "isIsolated": plantation.is_isolated,
        "immunityUntilTurn": plantation.immunity_until_turn,
        "hp": plantation.hp,
    }


def point_to_payload(point: object) -> dict[str, int]:
    return {"x": point.x, "y": point.y}
