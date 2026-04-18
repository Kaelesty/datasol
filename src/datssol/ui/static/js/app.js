const config = window.DATSSOL_UI_CONFIG;

const state = {
  server: config.defaultServer,
  logsTail: config.defaultLogsTail,
  autoRefresh: true,
  intervalId: null,
  bot: {
    running: false,
    profile: config.defaultBotProfile,
    server: config.defaultServer,
  },
};

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  syncServerButtons();
  syncServerLabel();
  dispatchServerChanged();
  startAutoRefresh();
  refreshAll();
});

function bindEvents() {
  document.querySelectorAll("[data-server]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.server = button.dataset.server;
      syncServerButtons();
      syncServerLabel();
      dispatchServerChanged();
      if (!state.bot.running) {
        await controlBot("set_server", { server: state.server }, { suppressErrors: true, refresh: false });
      }
      refreshAll();
    });
  });

  document.getElementById("refresh-arena").addEventListener("click", refreshArena);
  document.getElementById("refresh-logs").addEventListener("click", refreshLogs);
  document.getElementById("bot-refresh").addEventListener("click", refreshBotState);
  document.getElementById("apply-tail").addEventListener("click", () => {
    const value = Number.parseInt(document.getElementById("logs-tail").value, 10);
    state.logsTail = Number.isNaN(value) ? config.defaultLogsTail : Math.max(0, value);
    document.getElementById("logs-tail").value = String(state.logsTail);
    refreshLogs();
  });

  document.getElementById("auto-refresh").addEventListener("change", (event) => {
    state.autoRefresh = event.target.checked;
    if (state.autoRefresh) {
      startAutoRefresh();
      refreshAll();
      return;
    }
    stopAutoRefresh();
  });

  document.getElementById("bot-profile").addEventListener("change", async (event) => {
    await controlBot("set_profile", { profile: event.target.value }, { refresh: true });
  });
  document.getElementById("bot-start").addEventListener("click", async () => {
    await controlBot(
      "start",
      {
        server: state.server,
        profile: document.getElementById("bot-profile").value,
        allowProd: document.getElementById("bot-allow-prod").checked,
      },
      { refresh: true },
    );
    refreshAll();
  });
  document.getElementById("bot-stop").addEventListener("click", async () => {
    await controlBot("stop", {}, { refresh: true });
  });
}

function startAutoRefresh() {
  stopAutoRefresh();
  state.intervalId = window.setInterval(() => {
    if (!state.autoRefresh) {
      return;
    }
    refreshAll();
  }, 3000);
}

function stopAutoRefresh() {
  if (state.intervalId !== null) {
    window.clearInterval(state.intervalId);
    state.intervalId = null;
  }
}

function syncServerButtons() {
  document.querySelectorAll("[data-server]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.server === state.server);
  });
}

function syncServerLabel() {
  document.getElementById("server-url").textContent = config.servers[state.server];
}

async function refreshAll() {
  await Promise.all([refreshArena(), refreshLogs(), refreshBotState()]);
}

async function refreshArena() {
  const errorNode = document.getElementById("arena-error");
  hideError(errorNode);

  try {
    const response = await fetchJson(`/api/ui/arena?server=${encodeURIComponent(state.server)}`);
    if (!response.ok) {
      showError(errorNode, response.error || "Arena request failed.");
      clearArena();
      dispatchArenaError(response.error || "Arena request failed.");
      return;
    }
    renderArena(response.data);
    dispatchArenaUpdated(response.data);
  } catch (error) {
    showError(errorNode, String(error));
    clearArena();
    dispatchArenaError(String(error));
  }
}

async function refreshLogs() {
  const errorNode = document.getElementById("logs-error");
  hideError(errorNode);

  try {
    const response = await fetchJson(
      `/api/ui/logs?server=${encodeURIComponent(state.server)}&tail=${encodeURIComponent(state.logsTail)}`,
    );
    if (!response.ok) {
      showError(errorNode, response.error || "Logs request failed.");
      clearLogs();
      return;
    }
    renderLogs(response.data);
  } catch (error) {
    showError(errorNode, String(error));
    clearLogs();
  }
}

async function refreshBotState() {
  const errorNode = document.getElementById("bot-error");
  hideError(errorNode);

  try {
    const response = await fetchJson("/api/ui/bot/state");
    if (!response.ok) {
      showError(errorNode, response.error || "Bot state request failed.");
      clearBotState();
      return;
    }
    renderBotState(response.data);
  } catch (error) {
    showError(errorNode, String(error));
    clearBotState();
  }
}

async function controlBot(action, payload, options = {}) {
  const { suppressErrors = false, refresh = true } = options;
  const errorNode = document.getElementById("bot-error");
  hideError(errorNode);

  try {
    const response = await postJson("/api/ui/bot/control", { action, ...payload });
    if (!response.ok) {
      if (!suppressErrors) {
        showError(errorNode, response.error || "Bot control request failed.");
      }
      return null;
    }
    renderBotState(response.data);
    if (refresh) {
      await refreshBotState();
    }
    return response.data;
  } catch (error) {
    if (!suppressErrors) {
      showError(errorNode, String(error));
    }
    return null;
  }
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return response.json();
}

function renderArena(data) {
  document.getElementById("turn-no").textContent = data.turnNo ?? "-";
  document.getElementById("next-turn").textContent =
    data.nextTurnIn == null ? "-" : `${data.nextTurnIn.toFixed(3)}s`;
  document.getElementById("map-size").textContent = `${data.size.width} x ${data.size.height}`;
  document.getElementById("action-range").textContent = String(data.actionRange ?? "-");

  renderCounts(data.counts || {});
  renderUpgrades(data.upgrades);
  renderPlantations(data.plantations || []);
  renderMeteo(data.meteoForecasts || []);
  renderCells(data.cells || []);
}

function renderCounts(counts) {
  const labels = [
    ["own", "Own"],
    ["enemy", "Enemy"],
    ["cells", "Cells"],
    ["construction", "Construction"],
    ["beavers", "Beavers"],
    ["mountains", "Mountains"],
    ["meteo", "Meteo"],
  ];
  const node = document.getElementById("counts-grid");
  node.innerHTML = labels
    .map(
      ([key, label]) => `
        <article class="count-chip">
          <span class="muted-label">${label}</span>
          <strong>${counts[key] ?? 0}</strong>
        </article>
      `,
    )
    .join("");
}

function renderUpgrades(upgrades) {
  const summaryNode = document.getElementById("upgrade-summary");
  const tiersNode = document.getElementById("upgrade-tiers");

  if (!upgrades) {
    summaryNode.innerHTML = `<div class="empty-state">No upgrade data.</div>`;
    tiersNode.innerHTML = "";
    return;
  }

  summaryNode.innerHTML = `
    <div class="list-item">
      <div class="list-item__title">
        <span>Points</span>
        <span>${upgrades.points}/${upgrades.maxPoints}</span>
      </div>
      <div class="list-item__meta">
        Next in ${upgrades.turnsUntilPoints} turns, interval ${upgrades.intervalTurns}
      </div>
    </div>
  `;

  tiersNode.innerHTML = (upgrades.tiers || [])
    .map(
      (tier) => `
        <article class="tag-chip">
          <span class="muted-label">${escapeHtml(tier.name)}</span>
          <strong>${tier.current}/${tier.max}</strong>
        </article>
      `,
    )
    .join("");
}

function renderPlantations(plantations) {
  const node = document.getElementById("plantations-list");
  if (!plantations.length) {
    node.innerHTML = `<div class="empty-state">No visible plantations.</div>`;
    return;
  }

  node.innerHTML = plantations
    .map((plantation) => {
      const role = plantation.isMain ? "MAIN" : "PLANTATION";
      const immunity =
        plantation.immunityUntilTurn == null ? "none" : String(plantation.immunityUntilTurn);
      return `
        <article class="list-item">
          <div class="list-item__title">
            <span>${role}</span>
            <span>HP ${plantation.hp}</span>
          </div>
          <div class="list-item__meta">id: ${escapeHtml(plantation.id)}</div>
          <div class="stack-block">
            pos: [${plantation.position.x}, ${plantation.position.y}]<br />
            isolated: ${plantation.isIsolated}<br />
            immunity until: ${immunity}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderMeteo(forecasts) {
  const node = document.getElementById("meteo-list");
  if (!forecasts.length) {
    node.innerHTML = `<div class="empty-state">No active or forecasted events.</div>`;
    return;
  }

  node.innerHTML = forecasts
    .map((forecast) => {
      const details = [];
      if (forecast.turnsUntil != null) {
        details.push(`turns until: ${forecast.turnsUntil}`);
      }
      if (forecast.id) {
        details.push(`id: ${escapeHtml(forecast.id)}`);
      }
      if (forecast.forming != null) {
        details.push(`forming: ${forecast.forming}`);
      }
      if (forecast.radius != null) {
        details.push(`radius: ${forecast.radius}`);
      }
      if (forecast.position) {
        details.push(`pos: [${forecast.position.x}, ${forecast.position.y}]`);
      }
      if (forecast.nextPosition) {
        details.push(`next: [${forecast.nextPosition.x}, ${forecast.nextPosition.y}]`);
      }
      return `
        <article class="list-item">
          <div class="list-item__title">
            <span>${escapeHtml(forecast.kind)}</span>
          </div>
          <div class="stack-block">${details.join("<br />") || "No extra details."}</div>
        </article>
      `;
    })
    .join("");
}

function renderCells(cells) {
  const node = document.getElementById("cells-list");
  const caption = document.getElementById("cells-caption");
  caption.textContent = `${cells.length} tracked`;

  if (!cells.length) {
    node.innerHTML = `<div class="empty-state">No terraformed cells in view.</div>`;
    return;
  }

  node.innerHTML = cells
    .map(
      (cell) => `
        <article class="list-item">
          <div class="list-item__title">
            <span>[${cell.position.x}, ${cell.position.y}]</span>
            <span>${formatNumber(cell.terraformationProgress)}%</span>
          </div>
          <div class="list-item__meta">
            degrades in: ${cell.turnsUntilDegradation == null ? "unknown" : cell.turnsUntilDegradation}
          </div>
        </article>
      `,
    )
    .join("");
}

function renderLogs(data) {
  const summaryNode = document.getElementById("logs-summary");
  const logsNode = document.getElementById("logs-list");

  if (data.error) {
    const details = (data.error.errors || []).join(" | ") || "Unknown logs error.";
    summaryNode.innerHTML = `<div class="empty-state">Server returned an error: ${escapeHtml(details)}</div>`;
    logsNode.innerHTML = "";
    return;
  }

  summaryNode.innerHTML = `
    <div class="list-item">
      <div class="list-item__title">
        <span>Total entries</span>
        <span>${data.totalEntries}</span>
      </div>
      <div class="list-item__meta">
        Showing ${data.tail === 0 ? "all" : `last ${data.tail}`} entries
      </div>
    </div>
  `;

  if (!(data.entries || []).length) {
    logsNode.innerHTML = `<div class="empty-state">No log entries.</div>`;
    return;
  }

  logsNode.innerHTML = data.entries
    .map(
      (entry) => `
        <article class="log-entry">
          <div class="log-entry__time">${escapeHtml(entry.time)}</div>
          <div class="log-entry__message">${escapeHtml(entry.message)}</div>
        </article>
      `,
    )
    .join("");
}

function renderBotState(data) {
  state.bot = {
    running: Boolean(data.running),
    profile: data.profile || config.defaultBotProfile,
    server: data.server || config.defaultServer,
    lastDecision: data.lastDecision || null,
  };

  document.getElementById("bot-profile").value = state.bot.profile;
  document.getElementById("bot-start").disabled = state.bot.running;
  document.getElementById("bot-stop").disabled = !state.bot.running;

  renderBotStatus(data);
  renderBotCounts(data);
  renderBotDecision(data.lastDecision);
  renderBotGuard(data);
  dispatchBotStateUpdated(data);
}

function renderBotStatus(data) {
  const node = document.getElementById("bot-status");
  const runtime = state.bot.running ? "Running" : "Stopped";
  node.innerHTML = `
    <div class="list-item">
      <div class="list-item__title">
        <span>Status</span>
        <span>${runtime}</span>
      </div>
      <div class="stack-block">
        Bot server: ${escapeHtml(data.server || "-")}<br />
        Viewer server: ${escapeHtml(state.server)}<br />
        Profile: ${escapeHtml(data.profile || config.defaultBotProfile)}<br />
        Last seen turn: ${data.lastSeenTurn ?? "-"}<br />
        Last submitted turn: ${data.lastSubmittedTurn ?? "-"}
      </div>
    </div>
  `;
}

function renderBotCounts(data) {
  const node = document.getElementById("bot-counts");
  const counts = [
    ["Submitted", data.submittedCount ?? 0],
    ["Skipped", data.skippedCount ?? 0],
    ["Rejected", data.rejectedCount ?? 0],
    ["Errors", data.errorCount ?? 0],
  ];
  node.innerHTML = counts
    .map(
      ([label, value]) => `
        <article class="count-chip">
          <span class="muted-label">${label}</span>
          <strong>${value}</strong>
        </article>
      `,
    )
    .join("");
}

function renderBotDecision(decision) {
  const node = document.getElementById("bot-decision");
  if (!decision) {
    node.innerHTML = `<div class="empty-state">No decisions yet.</div>`;
    return;
  }

  const actions = decision.actions || [];
  node.innerHTML = `
    <div class="list-item">
      <div class="list-item__title">
        <span>Turn ${decision.turnNo ?? "-"}</span>
        <span>Score ${formatScore(decision.estimatedScore)}</span>
      </div>
      <div class="list-item__meta">Profile: ${escapeHtml(decision.profile || config.defaultBotProfile)}</div>
      <div class="stack-block">${escapeHtml(decision.reason || "No decision reason.")}</div>
    </div>
    ${
      actions.length
        ? actions
            .map(
              (action) => `
                <article class="list-item">
                  <div class="stack-block">${escapeHtml(action)}</div>
                </article>
              `,
            )
            .join("")
        : '<div class="empty-state">No action breakdown available.</div>'
    }
  `;
}

function renderBotGuard(data) {
  const node = document.getElementById("bot-guard");
  if ((data.server || "") !== "prod") {
    node.innerHTML = "";
    return;
  }
  node.innerHTML = `
    <div class="message message--error">
      Prod mode is selected for the bot. Starting requires the explicit “Allow Prod Start” switch.
      ${data.lastError ? `<br /><br />Last error: ${escapeHtml(data.lastError)}` : ""}
    </div>
  `;
}

function clearArena() {
  document.getElementById("turn-no").textContent = "-";
  document.getElementById("next-turn").textContent = "-";
  document.getElementById("map-size").textContent = "-";
  document.getElementById("action-range").textContent = "-";
  document.getElementById("counts-grid").innerHTML = `<div class="empty-state">No arena data.</div>`;
  document.getElementById("upgrade-summary").innerHTML = `<div class="empty-state">No upgrade data.</div>`;
  document.getElementById("upgrade-tiers").innerHTML = "";
  document.getElementById("plantations-list").innerHTML = `<div class="empty-state">No plantation data.</div>`;
  document.getElementById("meteo-list").innerHTML = `<div class="empty-state">No meteo data.</div>`;
  document.getElementById("cells-list").innerHTML = `<div class="empty-state">No cell data.</div>`;
  document.getElementById("cells-caption").textContent = "-";
}

function dispatchServerChanged() {
  window.dispatchEvent(
    new CustomEvent("datssol:server-changed", {
      detail: { server: state.server },
    }),
  );
}

function dispatchArenaUpdated(arena) {
  window.dispatchEvent(
    new CustomEvent("datssol:arena-updated", {
      detail: { server: state.server, arena },
    }),
  );
}

function dispatchArenaError(error) {
  window.dispatchEvent(
    new CustomEvent("datssol:arena-error", {
      detail: { server: state.server, error },
    }),
  );
}

window.datssolRefreshArena = refreshArena;
window.datssolState = state;

function clearLogs() {
  document.getElementById("logs-summary").innerHTML = `<div class="empty-state">No logs data.</div>`;
  document.getElementById("logs-list").innerHTML = "";
}

function clearBotState() {
  state.bot = {
    running: false,
    profile: config.defaultBotProfile,
    server: config.defaultServer,
    lastDecision: null,
  };
  document.getElementById("bot-status").innerHTML = `<div class="empty-state">No bot state.</div>`;
  document.getElementById("bot-counts").innerHTML = "";
  document.getElementById("bot-decision").innerHTML = `<div class="empty-state">No decisions yet.</div>`;
  document.getElementById("bot-guard").innerHTML = "";
  document.getElementById("bot-start").disabled = false;
  document.getElementById("bot-stop").disabled = true;
  dispatchBotStateUpdated({ running: false, profile: config.defaultBotProfile, server: config.defaultServer, lastDecision: null });
}

function dispatchBotStateUpdated(botState) {
  window.dispatchEvent(
    new CustomEvent("datssol:bot-state-updated", {
      detail: { botState },
    }),
  );
}

function showError(node, message) {
  node.textContent = message;
  node.classList.remove("hidden");
}

function hideError(node) {
  node.textContent = "";
  node.classList.add("hidden");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatNumber(value) {
  return Number.isInteger(value) ? String(value) : Number(value).toFixed(1);
}

function formatScore(value) {
  const numeric = Number(value ?? 0);
  return Number.isFinite(numeric) ? numeric.toFixed(1) : "0.0";
}
