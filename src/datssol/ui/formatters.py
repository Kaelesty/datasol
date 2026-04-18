"""Console formatters for read-only views."""

from __future__ import annotations

from datssol.model import ArenaState
from datssol.model import LogEntry
from datssol.model import LogsResponse
from datssol.model import Plantation


def format_arena(state: ArenaState) -> str:
    lines: list[str] = []
    lines.append("Arena")
    lines.append(f"Turn: {state.turn_no}")
    lines.append(f"Next turn in: {state.next_turn_in:.3f}s")
    lines.append(f"Map size: {state.size.width} x {state.size.height}")
    lines.append(f"Action range: {state.action_range}")
    lines.append(
        "Counts: "
        f"own={len(state.plantations)} "
        f"enemy={len(state.enemy)} "
        f"cells={len(state.cells)} "
        f"construction={len(state.construction)} "
        f"beavers={len(state.beavers)} "
        f"mountains={len(state.mountains)} "
        f"meteo={len(state.meteo_forecasts)}"
    )

    if state.plantation_upgrades is not None:
        upgrades = state.plantation_upgrades
        lines.append(
            "Upgrades: "
            f"points={upgrades.points}/{upgrades.max_points}, "
            f"next in {upgrades.turns_until_points} turns"
        )
        if upgrades.tiers:
            tier_summary = ", ".join(
                f"{tier.name}={tier.current}/{tier.max}" for tier in upgrades.tiers
            )
            lines.append(f"Tiers: {tier_summary}")

    if state.plantations:
        lines.append("Own plantations:")
        for plantation in state.plantations:
            lines.append(f"  - {format_plantation(plantation)}")

    if state.cells:
        lines.append("Known terraformed cells:")
        for cell in state.cells[:5]:
            lines.append(
                "  - "
                f"[{cell.position.x}, {cell.position.y}] "
                f"progress={cell.terraformation_progress:g} "
                f"degrades in={cell.turns_until_degradation}"
            )
        if len(state.cells) > 5:
            lines.append(f"  ... and {len(state.cells) - 5} more")

    if state.meteo_forecasts:
        lines.append("Meteo:")
        for forecast in state.meteo_forecasts:
            details = [f"kind={forecast.kind}", f"turns_until={forecast.turns_until}"]
            if forecast.id is not None:
                details.append(f"id={forecast.id}")
            if forecast.forming is not None:
                details.append(f"forming={forecast.forming}")
            if forecast.position is not None:
                details.append(f"pos=[{forecast.position.x}, {forecast.position.y}]")
            if forecast.next_position is not None:
                details.append(
                    f"next=[{forecast.next_position.x}, {forecast.next_position.y}]"
                )
            if forecast.radius is not None:
                details.append(f"radius={forecast.radius}")
            lines.append("  - " + ", ".join(details))

    return "\n".join(lines)


def format_logs(response: LogsResponse, tail: int = 20) -> str:
    if response.error is not None:
        if response.error.errors:
            return "Logs error:\n" + "\n".join(f"  - {item}" for item in response.error.errors)
        return "Logs error: unknown server error"

    entries = response.entries[-tail:] if tail > 0 else response.entries
    lines = [f"Logs: {len(response.entries)} entries"]
    for entry in entries:
        lines.append(f"  - {format_log_entry(entry)}")
    return "\n".join(lines)


def format_plantation(plantation: Plantation) -> str:
    role = "MAIN" if plantation.is_main else "PLANTATION"
    immunity = (
        f", immunity_until={plantation.immunity_until_turn}"
        if plantation.immunity_until_turn is not None
        else ""
    )
    return (
        f"{role} id={plantation.id} "
        f"pos=[{plantation.position.x}, {plantation.position.y}] "
        f"hp={plantation.hp} "
        f"isolated={plantation.is_isolated}"
        f"{immunity}"
    )


def format_log_entry(entry: LogEntry) -> str:
    return f"{entry.time} | {entry.message}"

