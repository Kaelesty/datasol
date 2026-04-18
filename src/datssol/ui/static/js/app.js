const config = window.DATSSOL_UI_CONFIG;

const state = {
  server: config.defaultServer,
  logsTail: config.defaultLogsTail,
  autoRefresh: true,
  intervalId: null,
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
    button.addEventListener("click", () => {
      state.server = button.dataset.server;
      syncServerButtons();
      syncServerLabel();
      dispatchServerChanged();
      refreshAll();
    });
  });

  document.getElementById("refresh-arena").addEventListener("click", refreshArena);
  document.getElementById("refresh-logs").addEventListener("click", refreshLogs);
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
}

function startAutoRefresh() {
  stopAutoRefresh();
  state.intervalId = window.setInterval(() => {
    if (!state.autoRefresh) {
      return;
    }
    refreshAll();
  }, 4000);
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
  await Promise.all([refreshArena(), refreshLogs()]);
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

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
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
