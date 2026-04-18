# AGENTS.md

## Purpose

This repository is no longer just a rules dump. It currently contains:
- the original DatSteam DatsSol rules PDF
- extracted rules text
- a Python codebase with `model`, `data`, and `ui` layers
- a local read-only web UI for inspecting live game state

This document is a practical guide for coding agents working on the project. It covers:
- game rules that matter for implementation
- current code architecture
- implemented features
- conscious limitations and constraints

Primary source files:
- `DatsSol.pdf`
- `DatsSol_extracted.txt`

Primary code entrypoint:
- `run_ui.py`

When the PDF, OpenAPI spec, and observed server behavior disagree, trust observed server behavior first, then the OpenAPI spec, then the PDF.

## Current Architecture

The codebase follows a lightweight three-layer structure:

### `model`

Path:
- `src/datssol/model/`

Responsibilities:
- immutable dataclass entities and value objects
- request and response models
- gateway interfaces via `Protocol`
- domain-level exceptions

Important files:
- `src/datssol/model/entities.py`
- `src/datssol/model/interfaces.py`
- `src/datssol/model/exceptions.py`

Notes:
- IDs are modeled as strings because the live server returns UUID-like identifiers for plantations and other entities.
- Some fields are intentionally looser than the PDF suggests because the real server is less strict than the documentation.

### `data`

Path:
- `src/datssol/data/`

Responsibilities:
- HTTP communication with the game server
- JSON parsing and normalization
- thin interactor wrappers for read and write use cases
- token loading

Important files:
- `src/datssol/data/requests_gateway.py`
- `src/datssol/data/interactors.py`
- `src/datssol/data/token_loader.py`

Notes:
- `RequestsGameApiGateway` is the concrete gateway implementation.
- It handles both documented error payloads (`code/errors`) and observed alternative payloads (`errCode/error`).
- The gateway already supports `submit_command(...)`, but the current UI does not expose write operations.

### `ui`

Path:
- `src/datssol/ui/`

Current product UI:
- local Flask web UI

Important files:
- `src/datssol/ui/web_app.py`
- `src/datssol/ui/web_presenters.py`
- `src/datssol/ui/templates/index.html`
- `src/datssol/ui/static/js/app.js`
- `src/datssol/ui/static/js/map.js`
- `src/datssol/ui/static/css/style.css`

Entrypoint:
- `run_ui.py`

Notes:
- The browser UI is the primary supported interface.
- A terminal UI file still exists in `src/datssol/ui/main.py`, but it is not the main product entrypoint anymore and should be treated as legacy/dev-only unless explicitly revived.

## Current Product Scope

The application is intentionally read-only at the UI level.

Implemented user-facing capabilities:
- inspect live arena state
- inspect player logs
- switch between `test` and `prod`
- auto-refresh the dashboard
- see a live tactical map integrated into the main page
- pan and zoom the map
- hover cells to inspect known entities on a coordinate

Implemented backend capabilities that are not yet exposed in the product UI:
- build `CommandRequest`
- submit `POST /api/command`
- buy upgrades via `plantationUpgrade`
- relocate main via `relocateMain`

Conscious scope decision:
- keep the browser UI read-only until validation and safety checks for write actions are implemented properly

## Current Web UI Behavior

The main page is the only intended user-facing screen.

Current behavior:
- top section: server selection and global status
- integrated tactical map near the top of the page
- arena dashboard below the map
- logs panel on the right

Map behavior:
- uses the same arena snapshot as the main dashboard
- does not fetch its own independent arena state anymore
- preserves zoom and pan across ordinary refreshes
- only refits the view when the arena context changes, currently defined by server and map dimensions

Map rendering includes:
- own plantations
- enemy plantations
- constructions
- beaver lairs
- mountains
- terraformed cells
- meteo markers
- boosted-cell highlighting for cells where both coordinates are divisible by 7

Iconography:
- the tactical map uses embedded SVG path data derived from official Heroicons assets
- these are drawn into the canvas via `Path2D`
- runtime does not fetch icons from the network

## Current API Surface In The Project

Documented game endpoints used by this project:
1. `GET /api/arena`
2. `GET /api/logs`
3. `POST /api/command`

Read endpoints currently used by the web UI:
1. `GET /api/arena`
2. `GET /api/logs`

Internal app endpoints exposed by the Flask layer:
1. `GET /`
2. `GET /api/ui/meta`
3. `GET /api/ui/arena`
4. `GET /api/ui/logs`

The Flask app does not expose any write endpoint to the browser.

## Conscious Limitations

These are deliberate project constraints at the current stage:

1. No write actions from the browser UI.
2. No persistent local database or snapshot history.
3. No authentication UI; token is loaded from `.token`.
4. No bot strategy engine yet.
5. No command validation engine yet.
6. No simulation layer for move preview yet.
7. No tests for UI behavior yet.
8. No websocket or push-based live updates; the UI polls periodically.
9. No map diff visualization between turns yet.
10. No production-grade packaging yet; the app is launched locally via `python run_ui.py`.

## Dev Commands

Primary local launch:
- `python run_ui.py`

Backend auto-restart on Python code changes:
- PowerShell from repo root:
- `powershell -ExecutionPolicy Bypass -File .\scripts\run_web_ui_dev.ps1`

What this does:
- sets `PYTHONPATH` to the local `src/`
- runs Flask against `datssol.ui.web_app:create_app`
- enables the Flask debug reloader so backend code changes restart automatically

Notes:
- this is for local development only
- browser assets still require a normal page refresh to see frontend changes
- do not use this command as the production launch path

## Write Capabilities Present But Not Exposed

The codebase already has the domain and data plumbing for write operations.

Existing write primitives in code:
- `CommandRequest`
- `PlantationAction`
- `ActionPath`
- `RelocateMainPath`
- `SubmitCommandInteractor`
- `RequestsGameApiGateway.submit_command(...)`

These support:
- build
- repair
- sabotage
- beaver attack
- upgrade purchase
- main relocation

They are intentionally not wired into the browser UI yet.

Reason:
- unsafe to expose without range validation, connectivity validation, settlement-limit validation, and better user confirmation flows

## Practical Engineering Rules For This Repo

When changing the project, prefer these rules:

1. Keep `model` free of HTTP or Flask concerns.
2. Keep `data` responsible for protocol translation and server normalization.
3. Keep `ui` responsible for presentation only.
4. Do not make the browser UI issue raw game write requests directly.
5. Route all game-server communication through the gateway/interactor layer.
6. When the real server disagrees with the docs, update parsing code to match the real server and document the discrepancy.
7. Preserve read-only behavior in the main UI unless the user explicitly asks to extend write capabilities.
8. Avoid hidden write side effects inside read-only refresh code.
9. Treat map viewport continuity as a UX invariant; ordinary refreshes should not reset pan/zoom.
10. Prefer local embedded assets for critical map rendering rather than runtime third-party dependencies.

## Game Summary

DatsSol is a turn-based territory and scoring game.

You control a network of plantations connected to a Main Base (`CU`, control center). Each plantation:
- automatically terraforms the cell under itself every turn
- can also perform one active action per turn

Available active actions:
- build a new plantation
- repair one of your plantations
- sabotage an enemy plantation
- attack a beaver lair

The game is not about holding static territory forever. Expansion is disposable and cyclical:
- a plantation disappears when its current cell reaches 100% terraformation
- fully terraformed cells later decay and become relevant again

## Match Structure

- One turn is the basic time unit.
- Turn duration is documented as 1 second, but may change in testing.
- One round lasts 600 turns.
- Development resets between rounds.
- Score converted to round placement persists across rounds.
- The final winner is determined by total round points across all final rounds.

## Core Objects

### Map

- The map is an XY plane.
- Current map dimensions are server-defined and smaller than in earlier rule revisions.
- Cells are either desert or mountain.
- Desert cells can be terraformed and built on.
- Mountain cells cannot be terraformed or built on.

### Plantations

Default plantation stats:
- `HP`: current health
- `MHP`: max health, default 50
- `TS`: terraforming speed, default 5
- `CS`: construction speed, default 5
- `RS`: repair speed, default 5
- `SE`: sabotage efficiency, default 5
- `BE`: beaver lair damage efficiency, default 5
- `DS`: degradation speed, default 10
- `AR`: action range, default 2
- `SR`: signal range, default 3
- `VR`: vision range, default 3

Default plantation limit:
- 30 plantations

### Main Base / CU

The CU is the heart of your network.

Important properties:
- It also terraforms the cell under itself.
- Its role can be transferred to an adjacent plantation.
- After relocation, the old CU remains as a normal plantation.
- Relocation does not change plantation HP.

Critical failure rule:
- If you lose the CU for any reason, all your plantations are destroyed.
- You respawn from scratch.
- You lose 5% of your current score, rounded down, but at least 1 point.
- Purchased upgrades are preserved.

This makes CU safety one of the highest priorities in bot logic.

## Connectivity and Control

### Command Connectivity

You can command only plantations connected to the CU through an orthogonally adjacent chain.

Important:
- diagonal adjacency does not count for network connectivity
- losing connectivity isolates the plantation

Effects of isolation:
- you cannot command it
- it stops executing its previous command
- it continues terraforming its own cell
- that terraforming gives no points while isolated
- it gradually loses HP based on `DS`
- it still counts toward your plantation limit

If connectivity is restored, the plantation becomes normal again.

### Ranges Use Square Geometry

`AR`, `SR`, and `VR` are not circular.

A target is in range if:
- `abs(dx) <= R`
- `abs(dy) <= R`

This is Chebyshev / square range.

Implementation note:
- do not use Euclidean distance
- do not use Manhattan distance

## Turn Processing Order

The documented server processing order is:
1. plantation upgrades
2. repair / construction
3. sabotage
4. attack on beaver lairs
5. CU relocation
6. beaver attacks
7. degradation of isolated plantations
8. damage to unfinished constructions with no progress for 1 turn
9. terraformation and point gain
10. player respawn
11. natural disasters

Practical implications:
- an upgrade bought this turn should affect actions in the same turn
- repair happens before sabotage
- CU relocation happens after sabotage and lair attacks, but before beaver attacks
- disasters happen after respawn according to the document

## Action Routing and Throughput Penalty

Actions can be issued:
- directly from the author plantation
- through another friendly plantation used as the action exit point

The exit point must be within `SR`.

Critical routing rule:
- every additional command that goes through the same exit plantation loses 1 effective point of `CS`, `RS`, `SE`, or `BE`
- efficiency cannot go below 0

This means a bot should not route all actions through one hub if multiple exits are available.

## Construction Rules

- A plantation can build on any target cell within `AR`.
- Any number of plantations may contribute to the same construction.
- Construction is a separate unit type.
- `max_hp` upgrade does not apply to unfinished construction.
- Construction completes when its HP/progress reaches 50.
- Once completed, it becomes a normal plantation.
- The new plantation starts with HP equal to current `MHP`.

Contested construction:
- Different players can all build on the same cell with separate progress.
- If one finishes earlier, that plantation stays.
- If multiple players finish on the same turn, all progress is reset and they all have to start over.

New plantation immunity:
- For 3 turns after completion, the plantation is immune to enemy actions, natural disasters, and beaver attacks.

Construction decay:
- If an unfinished plantation gets no construction progress for one turn, it starts degrading using `DS`.

Plantation limit trap:
- If you begin building over the settlement limit, then on the first progress tick of the new construction, your oldest plantation disappears.
- Age is counted from construction completion time.
- If several oldest plantations share the same age, removal is random among them.
- This can destroy your CU.

Implementation note:
- every build command must pass a strict pre-check against plantation limit and CU survival

## Repair Rules

- A plantation can repair one of your other plantations.
- It cannot repair itself.
- Repair amount per turn is based on `RS`.

## Sabotage Rules

- A plantation can sabotage an enemy plantation.
- Damage per turn is based on `SE`.
- If enemy HP reaches 0, the plantation is destroyed.
- The attacker gains as many victory points as that cell could have produced.

Shared kill rule:
- if multiple players sabotage the same target, points go to the player who dealt the most damage on the last turn
- if tied, points are split evenly

Critical edge case:
- you cannot attack an unfinished enemy construction directly
- instead, your action becomes your own construction on that same cell under normal construction rules

Also:
- the terraformation progress of a cell is preserved after the plantation on it is destroyed

## Terraformation Rules

- All cells start at 0% terraformation progress.
- A plantation automatically adds `TS` progress to its own cell each turn.
- No separate command is required.

Scoring:
- normal cell: maximum 1000 points total
- boosted cell: maximum 1500 points total
- boosted cells are those where both `X` and `Y` are divisible by 7
- each 1% of terraformation gives:
- 10 points on a normal cell
- 15 points on a boosted cell

Critical lifecycle rule:
- when a cell reaches 100% terraformation, the plantation on it disappears

Late decay rule:
- after 20 turns, a fully terraformed cell begins losing 10% progress per turn
- documented timing may change after testing rounds

Strategic consequence:
- plantations are disposable scoring units
- expansion must be continuous
- boosted cells are high-value targets and should be prioritized

## Beaver Lairs

- Beaver lairs exist across the map.
- They attack plantations in their range.
- Documented beaver lair attack range is `AR = 2`.
- Beaver attacks also affect unfinished construction.
- Each attack deals 15 HP damage.

Lair stats:
- 100 HP
- regenerates 5 HP per turn

Reward:
- destroying a lair gives 20x the points that the cell could have produced

Shared kill rule:
- points go to the player who dealt the most damage on the last turn
- if tied, points are split evenly

After destruction:
- the cell becomes available for terraformation

## Natural Disasters

### Sandstorms

- At most one sandstorm may exist at a time.
- A sandstorm forms in a random point and then moves diagonally across the map.
- It always passes through the map center.
- It needs 5 turns to fully form.
- While forming, it does not deal damage.
- When active, it deals 2 HP per turn to plantations in its area.
- It cannot kill a plantation; it can only reduce HP to 1.
- Movement speed is randomly chosen at spawn, between 5 and 15 cells per turn.

Players receive storm information including:
- current position
- speed
- radius
- name

### Earthquakes

- Earthquakes instantly deal 10 HP damage to all plantations and all constructions.
- Documented chance per turn is 5%.
- If a plantation is destroyed by an earthquake, nobody gets sabotage victory points for previously damaging it.

## Upgrades

Upgrade points:
- 1 point every 30 turns
- up to 15 total points can be obtained

Documented upgrade branches:
- `repair_power`: +1 repair power, max 3
- `max_hp`: +10 max HP, max 5
- `settlement_limit`: +1 plantation limit, max 10
- `signal_range`: +1 signal range
- `decay_mitigation`: reduces `DS` by 2, max 3
- `earthquake_mitigation`: reduces earthquake damage by 2, max 3
- `beaver_damage_mitigation`: reduces beaver attack damage by 2, max 5
- `vision_range`: +2 vision range, max 5

Important note:
- the rules text says the degradation and some mitigation effects also apply to construction
- `repair_power` appears to affect both repair and construction in practice and in the API naming

## Winning

Round score sources:
- terraformation
- sabotage
- destroying beaver lairs

Placement within a round is based on score.
Final winner is based on total round points across all final rounds.

Tie-breakers across final rounds:
1. more total round points
2. fewer lost CUs
3. more destroyed beavers
4. more sabotages

There is also a guarantee of at least 1 round point if a team finishes the round with score above 0.

## Achievements

The PDF documents achievement conditions for specific final rounds. These are not core mechanics for a competitive bot, but they may matter for side objectives or event play.

## API Summary

### Authentication

All requests require:
- `X-Auth-Token: <your_token>`

### Coordinates

Coordinates are arrays:
- `[x, y]`

### `GET /api/arena`

Returns current visible game state.

Important fields:
- `turnNo`
- `nextTurnIn`
- `size`
- `actionRange`
- `plantations[]`
- `enemy[]`
- `mountains[]`
- `cells[]`
- `construction[]`
- `beavers[]`
- `plantationUpgrades`
- `meteoForecasts[]`

Useful plantation fields:
- `id`
- `position`
- `isMain`
- `isIsolated`
- `immunityUntilTurn`
- `hp`

Useful cell fields:
- `position`
- `terraformationProgress`
- `turnsUntilDegradation`

Useful construction fields:
- `position`
- `progress`

Useful upgrade fields:
- `points`
- `intervalTurns`
- `turnsUntilPoints`
- `maxPoints`
- `tiers[]`

Useful weather fields:
- `kind`
- `turnsUntil`
- `id`
- `forming`
- `position`
- `nextPosition`
- `radius`

### `POST /api/command`

Sends actions for the current turn.

Main request fields:
- `command`
- `plantationUpgrade`
- `relocateMain`

Action path format:
- first coordinate: command author
- second coordinate: action exit point
- third coordinate: target

Action type is inferred from target:
- own plantation -> repair
- enemy plantation -> sabotage
- beaver target -> attack
- empty cell -> construction

`relocateMain` uses a path like:
- `[[fromX, fromY], [toX, toY]]`

Critical API rule:
- the server expects at least one useful action per turn
- you must send at least one of:
- `command`
- `plantationUpgrade`
- `relocateMain`

Otherwise you may receive an error like:
- `empty command: no plantation actions, no relocateMain, and no plantationUpgrade provided`

Important API robustness rule:
- a response may still contain `code: 0` while reporting errors in `errors[]`
- do not treat `code == 0` as enough
- always inspect `errors[]`

Observed/ documented error examples:
- `command already submitted this turn`
- `empty command: no plantation actions, no relocateMain, and no plantationUpgrade provided`

### `GET /api/logs`

Returns player logs.

If the token is not registered in the game, the server returns an error object instead of a log array.

## Implementation Priorities For Agents

If you are writing or reviewing a bot, prioritize these concerns:

1. Preserve CU safety.
2. Track orthogonal connectivity to CU every turn.
3. Use square range math for `AR`, `SR`, and `VR`.
4. Model turn phase order correctly.
5. Spread action routing load across multiple exit plantations.
6. Exploit boosted cells where `x % 7 == 0` and `y % 7 == 0`.
7. Treat plantations as disposable scoring units, not permanent assets.
8. Prevent over-limit construction from deleting critical old plantations.
9. Parse API responses defensively and always inspect `errors[]`.
10. Validate assumptions against live server behavior whenever rules wording is ambiguous.

## Common Bot Failure Modes

Avoid these mistakes:
- treating ranges as circles
- treating diagonal connectivity as valid for CU network control
- routing too many actions through one exit plantation
- ignoring that a plantation disappears at 100% terraformation
- ignoring 3-turn immunity on newly completed plantations
- assuming empty commands are harmless
- assuming `code: 0` means success
- forgetting that sabotage cannot directly attack unfinished enemy construction
- building past the settlement limit without checking whether the oldest plantation is the CU or a critical bridge

## Recommended Validation Checklist

Before submitting commands each turn, a robust bot should check:

1. Is the CU safe this turn under known enemy, beaver, and disaster threats?
2. Will any planned build exceed settlement limit?
3. If yes, which plantation would be removed, and does that break CU safety or connectivity?
4. Are all commanded source and exit plantations connected to the CU?
5. Are all target coordinates in square range?
6. Has routing load reduced effective `CS`, `RS`, `SE`, or `BE` to a bad value?
7. Is there at least one useful action in the outgoing request?
8. If buying an upgrade, is it the best tempo use of the turn?
9. Does any target have immunity that makes the action pointless?
10. After receiving the response, did `errors[]` stay empty?
