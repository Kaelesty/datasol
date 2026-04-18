const mapConfig = window.DATSSOL_MAP_CONFIG;

const mapState = {
  server: window.datssolState?.server || mapConfig.defaultServer,
  arena: null,
  viewportKey: null,
  transform: {
    scale: 14,
    offsetX: 40,
    offsetY: 40,
  },
  pointer: {
    dragging: false,
    lastX: 0,
    lastY: 0,
    hoverCell: null,
  },
  autoRefreshId: null,
  botDecision: null,
};

const HEROICON_PATHS = {
  own: new Path2D(
    "M13.5 21V13.5C13.5 13.0858 13.8358 12.75 14.25 12.75H17.25C17.6642 12.75 18 13.0858 18 13.5V21M13.5 21H2.36088M13.5 21H18M18 21H21.6391M20.25 21V9.34876M3.75 21V9.349M3.75 9.349C4.89729 10.0121 6.38977 9.85293 7.37132 8.87139C7.41594 8.82677 7.45886 8.78109 7.50008 8.73444C8.04979 9.3572 8.85402 9.74998 9.75 9.74998C10.646 9.74998 11.4503 9.35717 12 8.73435C12.5497 9.35717 13.354 9.74998 14.25 9.74998C15.1459 9.74998 15.9501 9.35725 16.4998 8.73456C16.541 8.78114 16.5838 8.82675 16.6284 8.8713C17.61 9.85293 19.1027 10.0121 20.25 9.34876M3.75 9.349C3.52788 9.22062 3.31871 9.06142 3.12868 8.87139C1.95711 7.69982 1.95711 5.80032 3.12868 4.62875L4.31797 3.43946C4.59927 3.15816 4.9808 3.00012 5.37863 3.00012H18.6212C19.019 3.00012 19.4005 3.15816 19.6818 3.43946L20.871 4.62866C22.0426 5.80023 22.0426 7.69973 20.871 8.8713C20.6811 9.06125 20.472 9.2204 20.25 9.34876M6.75 18H10.5C10.9142 18 11.25 17.6642 11.25 17.25V13.5C11.25 13.0858 10.9142 12.75 10.5 12.75H6.75C6.33579 12.75 6 13.0858 6 13.5V17.25C6 17.6642 6.33579 18 6.75 18Z",
  ),
  enemy: new Path2D(
    "M2.25 21H21.75M3.75 3V21M14.25 3V21M20.25 7.5V21M6.75 6.75H7.5M6.75 9.75H7.5M6.75 12.75H7.5M10.5 6.75H11.25M10.5 9.75H11.25M10.5 12.75H11.25M6.75 21V17.625C6.75 17.0037 7.25368 16.5 7.875 16.5H10.125C10.7463 16.5 11.25 17.0037 11.25 17.625V21M3 3H15M14.25 7.5H21M17.25 11.25H17.2575V11.2575H17.25V11.25ZM17.25 14.25H17.2575V14.2575H17.25V14.25ZM17.25 17.25H17.2575V17.2575H17.25V17.25Z",
  ),
  construction: new Path2D(
    "M21 7.5L18.75 6.1875M21 7.5V9.75M21 7.5L18.75 8.8125M3 7.5L5.25 6.1875M3 7.5L5.25 8.8125M3 7.5V9.75M12 12.75L14.25 11.4375M12 12.75L9.75 11.4375M12 12.75V15M12 21.75L14.25 20.4375M12 21.75V19.5M12 21.75L9.75 20.4375M9.75 3.5625L12 2.25L14.25 3.5625M21 14.25V16.5L18.75 17.8125M5.25 17.8125L3 16.5V14.25",
  ),
  beaver: new Path2D(
    "M11.9997 12.75C13.1482 12.75 14.2778 12.8307 15.3833 12.9867C16.4196 13.1329 17.2493 13.9534 17.2493 15C17.2493 18.7279 14.8988 21.75 11.9993 21.75C9.09977 21.75 6.74927 18.7279 6.74927 15C6.74927 13.9535 7.57879 13.1331 8.61502 12.9868C9.72081 12.8307 10.8508 12.75 11.9997 12.75ZM11.9997 12.75C14.8825 12.75 17.6469 13.2583 20.2075 14.1901C20.083 16.2945 19.6873 18.3259 19.0549 20.25M11.9997 12.75C9.11689 12.75 6.35312 13.2583 3.79248 14.1901C3.91702 16.2945 4.31272 18.3259 4.94512 20.25M11.9997 12.75C13.2423 12.75 14.2498 11.7426 14.2498 10.5C14.2498 10.4652 14.249 10.4306 14.2475 10.3961M11.9997 12.75C10.757 12.75 9.74979 11.7426 9.74979 10.5C9.74979 10.4652 9.75058 10.4306 9.75214 10.3961M12.0002 8.25C12.995 8.25 13.971 8.16929 14.922 8.01406C15.3246 7.94835 15.6628 7.65623 15.7168 7.25196C15.7388 7.08776 15.7502 6.92021 15.7502 6.75C15.7502 6.11844 15.594 5.52335 15.3183 5.00121M12.0002 8.25C11.0053 8.25 10.0293 8.16929 9.0783 8.01406C8.67576 7.94835 8.33754 7.65623 8.28346 7.25196C8.26149 7.08777 8.25015 6.92021 8.25015 6.75C8.25015 6.1175 8.40675 5.52157 8.68327 4.99887M12.0002 8.25C10.7923 8.25 9.80641 9.20171 9.75214 10.3961M12.0002 8.25C13.208 8.25 14.1932 9.20171 14.2475 10.3961M8.68327 4.99887C8.25654 4.71496 7.86824 4.37787 7.52783 3.99707C7.59799 3.36615 7.7986 2.7746 8.10206 2.25M8.68327 4.99887C9.31221 3.81004 10.5616 3 12.0002 3C13.4397 3 14.6897 3.8111 15.3183 5.00121M15.3183 5.00121C15.7445 4.71804 16.1325 4.38184 16.4728 4.00201C16.4031 3.36924 16.2023 2.77597 15.898 2.25M4.92097 6C4.71594 7.08086 4.58339 8.18738 4.52856 9.3143C6.19671 9.86025 7.94538 10.2283 9.75214 10.3961M19.0786 6C19.2836 7.08086 19.4162 8.18738 19.471 9.3143C17.8029 9.86024 16.0542 10.2283 14.2475 10.3961",
  ),
  cloud: new Path2D(
    "M2.25 15C2.25 17.4853 4.26472 19.5 6.75 19.5H18C20.0711 19.5 21.75 17.8211 21.75 15.75C21.75 14.1479 20.7453 12.7805 19.3316 12.2433C19.4407 11.9324 19.5 11.5981 19.5 11.25C19.5 9.59315 18.1569 8.25 16.5 8.25C16.1767 8.25 15.8654 8.30113 15.5737 8.39575C14.9765 6.1526 12.9312 4.5 10.5 4.5C7.6005 4.5 5.25 6.85051 5.25 9.75C5.25 10.0832 5.28105 10.4092 5.3404 10.7252C3.54555 11.3167 2.25 13.0071 2.25 15Z",
  ),
  mountain: new Path2D(
    "M2.25 15.75L7.40901 10.591C8.28769 9.71231 9.71231 9.71231 10.591 10.591L15.75 15.75M14.25 14.25L15.659 12.841C16.5377 11.9623 17.9623 11.9623 18.841 12.841L21.75 15.75M3.75 19.5H20.25C21.0784 19.5 21.75 18.8284 21.75 18V6C21.75 5.17157 21.0784 4.5 20.25 4.5H3.75C2.92157 4.5 2.25 5.17157 2.25 6V18C2.25 18.8284 2.92157 19.5 3.75 19.5ZM14.25 8.25H14.2575V8.2575H14.25V8.25ZM14.625 8.25C14.625 8.45711 14.4571 8.625 14.25 8.625C14.0429 8.625 13.875 8.45711 13.875 8.25C13.875 8.04289 14.0429 7.875 14.25 7.875C14.4571 7.875 14.625 8.04289 14.625 8.25Z",
  ),
};

let canvas;
let ctx;

document.addEventListener("DOMContentLoaded", () => {
  canvas = document.getElementById("tactical-map");
  if (!canvas) {
    return;
  }
  ctx = canvas.getContext("2d");

  bindMapEvents();
  resizeCanvas();
  renderMapSummary(null);
  renderObjectPanel(null);
  renderHoverCard();
  drawMap();
});

function bindMapEvents() {
  window.addEventListener("resize", () => {
    resizeCanvas();
    drawMap();
  });

  document.getElementById("map-refresh").addEventListener("click", () => {
    window.datssolRefreshArena?.();
  });
  document.getElementById("map-reset-view").addEventListener("click", () => {
    fitArenaToView();
    drawMap();
  });
  document.getElementById("map-objects").addEventListener("click", (event) => {
    const target = event.target.closest("[data-focus-x][data-focus-y]");
    if (!target) {
      return;
    }
    focusCell(Number(target.dataset.focusX), Number(target.dataset.focusY));
  });

  window.addEventListener("datssol:server-changed", (event) => {
    mapState.server = event.detail.server;
    mapState.viewportKey = null;
  });

  window.addEventListener("datssol:arena-updated", (event) => {
    if (event.detail.server !== mapState.server) {
      return;
    }
    applyArenaSnapshot(event.detail.arena);
  });

  window.addEventListener("datssol:arena-error", (event) => {
    if (event.detail.server !== mapState.server) {
      return;
    }
    const errorNode = document.getElementById("map-error");
    mapState.arena = null;
    showError(errorNode, event.detail.error || "Arena request failed.");
    renderMapSummary(null);
    renderObjectPanel(null);
    renderHoverCard();
    drawMap();
  });

  window.addEventListener("datssol:bot-state-updated", (event) => {
    mapState.botDecision = event.detail.botState?.lastDecision || null;
    drawMap();
  });

  canvas.addEventListener("mousedown", (event) => {
    mapState.pointer.dragging = true;
    mapState.pointer.lastX = event.clientX;
    mapState.pointer.lastY = event.clientY;
  });

  window.addEventListener("mouseup", () => {
    mapState.pointer.dragging = false;
  });

  canvas.addEventListener("mousemove", (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    if (mapState.pointer.dragging) {
      const dx = event.clientX - mapState.pointer.lastX;
      const dy = event.clientY - mapState.pointer.lastY;
      mapState.transform.offsetX += dx;
      mapState.transform.offsetY += dy;
      mapState.pointer.lastX = event.clientX;
      mapState.pointer.lastY = event.clientY;
      drawMap();
      return;
    }

    mapState.pointer.hoverCell = screenToCell(x, y);
    renderHoverCard();
    drawMap();
  });

  canvas.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mouseX = event.clientX - rect.left;
      const mouseY = event.clientY - rect.top;
      const before = screenToWorld(mouseX, mouseY);
      const factor = event.deltaY < 0 ? 1.1 : 0.9;
      mapState.transform.scale = clamp(mapState.transform.scale * factor, 2, 60);
      const after = worldToScreen(before.x, before.y);
      mapState.transform.offsetX += mouseX - after.x;
      mapState.transform.offsetY += mouseY - after.y;
      drawMap();
    },
    { passive: false },
  );
}

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function applyArenaSnapshot(nextArena) {
  const errorNode = document.getElementById("map-error");
  hideError(errorNode);
  const nextViewportKey = buildViewportKey(mapState.server, nextArena);
  const shouldRefit = mapState.viewportKey !== nextViewportKey;
  const previousMain = getMainPosition(mapState.arena);
  const nextMain = getMainPosition(nextArena);
  const shouldFollowMain =
    !shouldRefit &&
    previousMain != null &&
    nextMain != null &&
    hasPositionChanged(previousMain, nextMain);

  mapState.arena = nextArena;
  if (shouldRefit) {
    fitArenaToView();
    mapState.viewportKey = nextViewportKey;
  }
  if (shouldFollowMain) {
    centerViewOnCell(nextMain.x, nextMain.y);
    mapState.pointer.hoverCell = { x: nextMain.x, y: nextMain.y };
  }
  renderMapSummary(mapState.arena);
  renderObjectPanel(mapState.arena);
  renderHoverCard();
  drawMap();
}

function drawMap() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  ctx.clearRect(0, 0, width, height);

  drawBackdrop(width, height);

  if (!mapState.arena) {
    drawPlaceholder("No arena snapshot");
    return;
  }

  const arena = mapState.arena;
  drawArenaPlate(arena.size.width, arena.size.height);
  drawBounds(arena.size.width, arena.size.height);
  drawBoostedCells(arena.size.width, arena.size.height);

  if (mapState.transform.scale >= 8) {
    drawGrid(arena.size.width, arena.size.height);
  }

  drawMountains(arena.mountains || []);
  drawCellProgress(arena.cells || []);
  drawMeteo(arena.meteoForecasts || []);
  drawConstruction(arena.construction || []);
  drawEntities(arena.enemy || [], "#be4a2f", 0.44, "enemy");
  drawEntities(arena.plantations || [], "#3f7b5c", 0.46, "own");
  drawEntities(arena.beavers || [], "#9860c8", 0.4, "beaver");
  drawBotPlanOverlay(mapState.botDecision);
  drawCoordinateLabels(arena.size.width, arena.size.height);
  drawHoverHighlight();
}

function drawBackdrop(width, height) {
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#fbf5ea");
  gradient.addColorStop(1, "#ede1cc");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
}

function drawPlaceholder(text) {
  ctx.fillStyle = "rgba(46, 34, 22, 0.55)";
  ctx.font = '600 18px "Space Grotesk"';
  ctx.textAlign = "center";
  ctx.fillText(text, canvas.clientWidth / 2, canvas.clientHeight / 2);
}

function drawArenaPlate(width, height) {
  const topLeft = worldToScreen(0, 0);
  ctx.fillStyle = "rgba(245, 236, 221, 0.92)";
  ctx.fillRect(
    topLeft.x,
    topLeft.y,
    width * mapState.transform.scale,
    height * mapState.transform.scale,
  );
}

function drawBounds(width, height) {
  const topLeft = worldToScreen(0, 0);
  ctx.strokeStyle = "rgba(58, 44, 30, 0.72)";
  ctx.lineWidth = 1.4;
  ctx.strokeRect(
    topLeft.x,
    topLeft.y,
    width * mapState.transform.scale,
    height * mapState.transform.scale,
  );
}

function drawBoostedCells(width, height) {
  const scale = mapState.transform.scale;
  if (scale < 4) {
    return;
  }

  const start = clamp(Math.floor(screenToWorld(0, 0).x), 0, width - 1);
  const end = clamp(Math.ceil(screenToWorld(canvas.clientWidth, 0).x), 0, width - 1);
  const startY = clamp(Math.floor(screenToWorld(0, 0).y), 0, height - 1);
  const endY = clamp(Math.ceil(screenToWorld(0, canvas.clientHeight).y), 0, height - 1);

  ctx.fillStyle = scale >= 10 ? "rgba(203, 141, 63, 0.11)" : "rgba(203, 141, 63, 0.07)";
  for (let x = start; x <= end; x += 1) {
    if (x % 7 !== 0) {
      continue;
    }
    for (let y = startY; y <= endY; y += 1) {
      if (y % 7 !== 0) {
        continue;
      }
      const pos = worldToScreen(x, y);
      ctx.fillRect(pos.x, pos.y, scale, scale);
    }
  }
}

function drawGrid(width, height) {
  ctx.strokeStyle = mapState.transform.scale >= 16 ? "rgba(94, 66, 34, 0.13)" : "rgba(94, 66, 34, 0.08)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0; x <= width; x += 1) {
    const start = worldToScreen(x, 0);
    const end = worldToScreen(x, height);
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
  }
  for (let y = 0; y <= height; y += 1) {
    const start = worldToScreen(0, y);
    const end = worldToScreen(width, y);
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
  }
  ctx.stroke();
}

function drawMountains(points) {
  points.forEach((point) => {
    const size = mapState.transform.scale;
    const center = worldToScreen(point.x + 0.5, point.y + 0.5);
    const radius = Math.max(3, size * 0.44);
    ctx.beginPath();
    ctx.fillStyle = "rgba(91, 78, 64, 0.92)";
    ctx.arc(center.x, center.y, radius * 1.15, 0, Math.PI * 2);
    ctx.fill();
    drawHeroIcon("mountain", center.x, center.y, radius * 1.65, "rgba(255, 247, 238, 0.95)", 1.4);
  });
}

function drawCellProgress(cells) {
  cells.forEach((cell) => {
    const pos = worldToScreen(cell.position.x, cell.position.y);
    const size = mapState.transform.scale;
    const progress = clamp(Number(cell.terraformationProgress || 0) / 100, 0, 1);
    ctx.fillStyle = `rgba(216, 167, 77, ${0.18 + progress * 0.55})`;
    ctx.fillRect(pos.x, pos.y, size, size);
  });
}

function drawConstruction(items) {
  items.forEach((item) => {
    const center = worldToScreen(item.position.x + 0.5, item.position.y + 0.5);
    const radius = Math.max(4, mapState.transform.scale * 0.46);
    ctx.beginPath();
    ctx.fillStyle = "rgba(207, 127, 47, 0.16)";
    ctx.arc(center.x, center.y, radius * 1.7, 0, Math.PI * 2);
    ctx.fill();
    drawHeroIcon("construction", center.x, center.y, radius * 2.2, "#cf7f2f", 1.8);
    if (mapState.transform.scale >= 12) {
      drawBadgeLabel(center.x, center.y + radius * 1.7, `C ${formatCompactNumber(item.progress)}`);
    }
  });
}

function drawEntities(items, color, radiusFactor, kind) {
  items.forEach((item) => {
    const position = item.position;
    const center = worldToScreen(position.x + 0.5, position.y + 0.5);
    const radius = Math.max(4, mapState.transform.scale * radiusFactor);
    ctx.beginPath();
    ctx.fillStyle = applyAlpha(color, kind === "enemy" ? 0.2 : 0.16);
    ctx.arc(center.x, center.y, radius * 1.75, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(255, 248, 240, 0.65)";
    ctx.lineWidth = 1.4;
    ctx.stroke();

    if (kind === "own" && item.isMain) {
      ctx.beginPath();
      ctx.strokeStyle = "rgba(63, 123, 92, 0.8)";
      ctx.lineWidth = 2.2;
      ctx.arc(center.x, center.y, radius * 1.7, 0, Math.PI * 2);
      ctx.stroke();
    }
    if (kind === "enemy") {
      ctx.beginPath();
      ctx.strokeStyle = "rgba(190, 74, 47, 0.42)";
      ctx.lineWidth = 1.6;
      ctx.arc(center.x, center.y, radius * 2.05, 0, Math.PI * 2);
      ctx.stroke();
    }

    const iconName = kind === "own" ? "own" : kind === "enemy" ? "enemy" : "beaver";
    drawHeroIcon(iconName, center.x, center.y, radius * 2.2, "rgba(255, 248, 240, 0.96)", 1.6);
    drawEntityLabel(item, center.x, center.y, radius, kind);
  });
}

function drawMeteo(forecasts) {
  forecasts.forEach((item) => {
    if (!item.position) {
      return;
    }
    const center = worldToScreen(item.position.x + 0.5, item.position.y + 0.5);
    const radius = Math.max(8, (item.radius || 4) * mapState.transform.scale);
    ctx.save();
    ctx.setLineDash(item.forming ? [8, 6] : [12, 8]);
    ctx.beginPath();
    ctx.fillStyle =
      item.kind === "sandstorm" ? "rgba(66, 123, 209, 0.08)" : "rgba(205, 84, 67, 0.08)";
    ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.strokeStyle = item.kind === "sandstorm" ? "rgba(66, 123, 209, 0.72)" : "rgba(205, 84, 67, 0.72)";
    ctx.lineWidth = 2;
    ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
    drawHeroIcon(
      "cloud",
      center.x,
      center.y,
      Math.max(12, radius * 0.75),
      item.kind === "sandstorm" ? "rgba(66, 123, 209, 0.92)" : "rgba(205, 84, 67, 0.92)",
      1.6,
    );

    if (item.nextPosition) {
      const next = worldToScreen(item.nextPosition.x + 0.5, item.nextPosition.y + 0.5);
      ctx.beginPath();
      ctx.strokeStyle =
        item.kind === "sandstorm" ? "rgba(66, 123, 209, 0.72)" : "rgba(205, 84, 67, 0.72)";
      ctx.lineWidth = 2;
      ctx.moveTo(center.x, center.y);
      ctx.lineTo(next.x, next.y);
      ctx.stroke();
      drawArrowHead(center, next, ctx.strokeStyle);
    }

    if (mapState.transform.scale >= 10) {
      const suffix = item.forming ? " forming" : "";
      drawBadgeLabel(center.x, center.y - Math.min(radius + 10, 32), `${item.kind}${suffix}`);
    }
  });
}

function drawCoordinateLabels(width, height) {
  if (mapState.transform.scale < 24) {
    return;
  }
  const startX = clamp(Math.floor(screenToWorld(0, 0).x), 0, width - 1);
  const endX = clamp(Math.ceil(screenToWorld(canvas.clientWidth, 0).x), 0, width - 1);
  const startY = clamp(Math.floor(screenToWorld(0, 0).y), 0, height - 1);
  const endY = clamp(Math.ceil(screenToWorld(0, canvas.clientHeight).y), 0, height - 1);

  ctx.fillStyle = "rgba(115, 92, 67, 0.62)";
  ctx.font = '500 10px "IBM Plex Mono"';
  ctx.textAlign = "left";
  for (let x = startX; x <= endX; x += 7) {
    for (let y = startY; y <= endY; y += 7) {
      const pos = worldToScreen(x, y);
      ctx.fillText(`${x},${y}`, pos.x + 3, pos.y + 12);
    }
  }
}

function drawBotPlanOverlay(decision) {
  if (!decision || !Array.isArray(decision.actionDetails) || !decision.actionDetails.length) {
    return;
  }

  decision.actionDetails.forEach((action) => {
    if (!action || !action.target) {
      return;
    }
    const target = worldToScreen(action.target.x + 0.5, action.target.y + 0.5);
    const actionColor = botActionColor(action.kind);

    if (action.author && action.exitPoint) {
      const author = worldToScreen(action.author.x + 0.5, action.author.y + 0.5);
      const exitPoint = worldToScreen(action.exitPoint.x + 0.5, action.exitPoint.y + 0.5);
      drawBotSegment(author, exitPoint, actionColor, false);
      drawBotSegment(exitPoint, target, actionColor, true);
    } else if (action.author) {
      const author = worldToScreen(action.author.x + 0.5, action.author.y + 0.5);
      drawBotSegment(author, target, actionColor, true);
    }

    const pulse = Math.max(6, mapState.transform.scale * 0.48);
    ctx.beginPath();
    ctx.strokeStyle = actionColor;
    ctx.lineWidth = 2;
    ctx.setLineDash(action.kind === "relocate_main" ? [7, 5] : []);
    ctx.arc(target.x, target.y, pulse, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);

    if (mapState.transform.scale >= 10) {
      drawBadgeLabel(target.x, target.y + pulse + 12, overlayLabel(action));
    }
  });
}

function drawBotSegment(from, to, color, arrow) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.4;
  ctx.setLineDash([8, 6]);
  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.stroke();
  ctx.restore();
  if (arrow) {
    drawArrowHead(from, to, color);
  }
}

function botActionColor(kind) {
  if (kind === "build") {
    return "rgba(41, 112, 77, 0.92)";
  }
  if (kind === "relocate_main") {
    return "rgba(35, 94, 168, 0.92)";
  }
  if (kind === "repair") {
    return "rgba(197, 102, 52, 0.92)";
  }
  if (kind === "sabotage") {
    return "rgba(190, 74, 47, 0.92)";
  }
  if (kind === "beaver") {
    return "rgba(152, 96, 200, 0.92)";
  }
  if (kind === "upgrade") {
    return "rgba(203, 141, 63, 0.92)";
  }
  return "rgba(57, 68, 78, 0.92)";
}

function overlayLabel(action) {
  if (action.kind === "build") {
    return action.summary.includes("continue construction") ? "CONTINUE" : "BUILD";
  }
  if (action.kind === "relocate_main") {
    return "RELOCATE";
  }
  return String(action.kind || "action").toUpperCase();
}

function drawHoverHighlight() {
  if (!mapState.pointer.hoverCell) {
    return;
  }
  const cell = mapState.pointer.hoverCell;
  const pos = worldToScreen(cell.x, cell.y);
  const size = mapState.transform.scale;
  ctx.strokeStyle = "rgba(46, 34, 22, 0.9)";
  ctx.lineWidth = 2;
  ctx.strokeRect(pos.x, pos.y, size, size);
}

function renderMapSummary(arena) {
  const node = document.getElementById("map-summary");
  const title = document.getElementById("map-status-title");
  const subtitle = document.getElementById("map-status-subtitle");

  if (!arena) {
    title.textContent = "Arena unavailable";
    subtitle.textContent = "The current snapshot could not be loaded.";
    node.innerHTML = `<div class="empty-state">No arena payload.</div>`;
    return;
  }

  title.textContent = `Turn ${arena.turnNo}`;
  subtitle.textContent = `Map ${arena.size.width} x ${arena.size.height}, next turn in ${arena.nextTurnIn}s`;
  node.innerHTML = `
    <div class="list-item">
      <div class="list-item__title">
        <span>Counts</span>
      </div>
      <div class="stack-block">
        Own: ${arena.counts.own}<br />
        Enemy: ${arena.counts.enemy}<br />
        Cells: ${arena.counts.cells}<br />
        Construction: ${arena.counts.construction}<br />
        Beavers: ${arena.counts.beavers}<br />
        Mountains: ${arena.counts.mountains}<br />
        Meteo: ${arena.counts.meteo}<br />
        Objects on map: ${countTrackedObjects(arena)}<br />
        Zoom: ${mapState.transform.scale.toFixed(1)}x
      </div>
    </div>
  `;
}

function renderObjectPanel(arena) {
  const node = document.getElementById("map-objects");
  const caption = document.getElementById("map-objects-caption");

  if (!arena) {
    caption.textContent = "-";
    node.innerHTML = `<div class="empty-state">Waiting for arena data.</div>`;
    return;
  }

  const objects = [
    ...(arena.plantations || []).map((item) => ({
      kind: "own",
      title: item.isMain ? "Own MAIN" : "Own plantation",
      value: `HP ${item.hp}`,
      x: item.position.x,
      y: item.position.y,
      meta: `pos=[${item.position.x}, ${item.position.y}] isolated=${item.isIsolated}`,
    })),
    ...(arena.enemy || []).map((item) => ({
      kind: "enemy",
      title: "Enemy plantation",
      value: `HP ${item.hp}`,
      x: item.position.x,
      y: item.position.y,
      meta: `pos=[${item.position.x}, ${item.position.y}] id=${escapeHtml(item.id)}`,
    })),
    ...(arena.beavers || []).map((item) => ({
      kind: "beaver",
      title: "Beaver lair",
      value: `HP ${item.hp}`,
      x: item.position.x,
      y: item.position.y,
      meta: `pos=[${item.position.x}, ${item.position.y}] id=${escapeHtml(item.id)}`,
    })),
    ...(arena.meteoForecasts || [])
      .filter((item) => item.position)
      .map((item) => ({
        kind: "meteo",
        title: item.kind,
        value: item.turnsUntil == null ? "active" : `T-${item.turnsUntil}`,
        x: item.position.x,
        y: item.position.y,
        meta: `pos=[${item.position.x}, ${item.position.y}] radius=${item.radius ?? "?"}${item.forming ? " forming" : ""}`,
      })),
  ];

  caption.textContent = `${objects.length} tracked`;
  if (!objects.length) {
    node.innerHTML = `<div class="empty-state">No visible objects in the current snapshot.</div>`;
    return;
  }

  node.innerHTML = objects
    .map(
      (item) => `
        <button
          type="button"
          class="object-chip object-chip--${item.kind}"
          data-focus-x="${item.x}"
          data-focus-y="${item.y}"
        >
          <div class="object-chip__title">
            <span>${escapeHtml(item.title)}</span>
            <span>${escapeHtml(item.value)}</span>
          </div>
          <div class="object-chip__meta">${item.meta}</div>
        </button>
      `,
    )
    .join("");
}

function renderHoverCard() {
  const node = document.getElementById("hover-card");
  const hover = mapState.pointer.hoverCell;
  const arena = mapState.arena;

  if (!hover || !arena) {
    node.innerHTML = `<div class="empty-state">Move the pointer over the map.</div>`;
    return;
  }

  const details = lookupCellDetails(arena, hover.x, hover.y);
  const rows = [`<strong>Cell [${hover.x}, ${hover.y}]</strong>`];

  if (!details.length) {
    rows.push(`<div class="list-item__meta">No known entities on this cell.</div>`);
  } else {
    rows.push(
      ...details.map(
        (item) => `<div class="stack-block"><span class="muted-label">${item.label}</span><br />${item.body}</div>`,
      ),
    );
  }

  node.innerHTML = rows.join("");
}

function lookupCellDetails(arena, x, y) {
  const details = [];
  arena.plantations
    .filter((item) => item.position.x === x && item.position.y === y)
    .forEach((item) =>
      details.push({
        label: item.isMain ? "Own MAIN" : "Own plantation",
        body: `id=${escapeHtml(item.id)}<br />hp=${item.hp}<br />isolated=${item.isIsolated}`,
      }),
    );
  arena.enemy
    .filter((item) => item.position.x === x && item.position.y === y)
    .forEach((item) =>
      details.push({
        label: "Enemy plantation",
        body: `id=${escapeHtml(item.id)}<br />hp=${item.hp}`,
      }),
    );
  arena.construction
    .filter((item) => item.position.x === x && item.position.y === y)
    .forEach((item) =>
      details.push({
        label: "Construction",
        body: `progress=${item.progress}`,
      }),
    );
  arena.beavers
    .filter((item) => item.position.x === x && item.position.y === y)
    .forEach((item) =>
      details.push({
        label: "Beaver lair",
        body: `id=${escapeHtml(item.id)}<br />hp=${item.hp}`,
      }),
    );
  arena.cells
    .filter((item) => item.position.x === x && item.position.y === y)
    .forEach((item) =>
      details.push({
        label: "Terraformed cell",
        body: `progress=${item.terraformationProgress}<br />degradesIn=${item.turnsUntilDegradation}`,
      }),
    );
  arena.mountains
    .filter((item) => item.x === x && item.y === y)
    .forEach(() =>
      details.push({
        label: "Terrain",
        body: "Mountain",
      }),
    );
  arena.meteoForecasts
    .filter((item) => item.position && item.position.x === x && item.position.y === y)
    .forEach((item) =>
      details.push({
        label: "Meteo anomaly",
        body:
          `kind=${escapeHtml(item.kind)}` +
          `<br />turnsUntil=${item.turnsUntil == null ? "active" : item.turnsUntil}` +
          `<br />radius=${item.radius == null ? "unknown" : item.radius}` +
          `<br />forming=${item.forming == null ? "unknown" : item.forming}`,
      }),
    );
  return details;
}

function drawEntityLabel(item, centerX, centerY, radius, kind) {
  if (mapState.transform.scale < 13) {
    return;
  }

  let label = "";
  if (kind === "own") {
    label = item.isMain ? `MAIN ${item.hp}` : `OWN ${item.hp}`;
  } else if (kind === "enemy") {
    label = `EN ${item.hp}`;
  } else if (kind === "beaver") {
    label = `BV ${item.hp}`;
  }
  if (!label) {
    return;
  }
  drawBadgeLabel(centerX, centerY - radius * 2.15, label);
}

function drawBadgeLabel(centerX, centerY, text) {
  ctx.save();
  ctx.font = '600 11px "IBM Plex Mono"';
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const paddingX = 7;
  const width = ctx.measureText(text).width + paddingX * 2;
  const height = 20;
  const x = centerX - width / 2;
  const y = centerY - height / 2;
  ctx.fillStyle = "rgba(255, 251, 244, 0.92)";
  ctx.strokeStyle = "rgba(58, 44, 30, 0.18)";
  ctx.lineWidth = 1;
  roundRect(ctx, x, y, width, height, 8);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "rgba(46, 34, 22, 0.88)";
  ctx.fillText(text, centerX, centerY + 0.5);
  ctx.restore();
}

function drawArrowHead(from, to, color) {
  const angle = Math.atan2(to.y - from.y, to.x - from.x);
  const size = 8;
  ctx.save();
  ctx.translate(to.x, to.y);
  ctx.rotate(angle);
  ctx.beginPath();
  ctx.fillStyle = color;
  ctx.moveTo(0, 0);
  ctx.lineTo(-size, size * 0.45);
  ctx.lineTo(-size, -size * 0.45);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function roundRect(context, x, y, width, height, radius) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.lineTo(x + width - radius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + radius);
  context.lineTo(x + width, y + height - radius);
  context.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  context.lineTo(x + radius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - radius);
  context.lineTo(x, y + radius);
  context.quadraticCurveTo(x, y, x + radius, y);
  context.closePath();
}

function focusCell(x, y) {
  if (!mapState.arena) {
    return;
  }
  const scale = Math.max(mapState.transform.scale, 12);
  mapState.transform.scale = scale;
  mapState.transform.offsetX = canvas.clientWidth / 2 - (x + 0.5) * scale;
  mapState.transform.offsetY = canvas.clientHeight / 2 - (y + 0.5) * scale;
  mapState.pointer.hoverCell = { x, y };
  renderHoverCard();
  drawMap();
}

function getMainPosition(arena) {
  if (!arena || !Array.isArray(arena.plantations)) {
    return null;
  }
  const main = arena.plantations.find((item) => item?.isMain && item.position);
  if (!main) {
    return null;
  }
  const x = Number(main.position.x);
  const y = Number(main.position.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return null;
  }
  return { x, y };
}

function hasPositionChanged(previous, next) {
  return previous.x !== next.x || previous.y !== next.y;
}

function centerViewOnCell(x, y) {
  const scale = clamp(mapState.transform.scale, 2, 60);
  mapState.transform.scale = scale;
  mapState.transform.offsetX = canvas.clientWidth / 2 - (x + 0.5) * scale;
  mapState.transform.offsetY = canvas.clientHeight / 2 - (y + 0.5) * scale;
}

function countTrackedObjects(arena) {
  return (
    (arena.plantations || []).length +
    (arena.enemy || []).length +
    (arena.beavers || []).length +
    (arena.meteoForecasts || []).filter((item) => item.position).length
  );
}

function formatCompactNumber(value) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) {
    return "0";
  }
  if (Math.abs(numeric) >= 100) {
    return numeric.toFixed(0);
  }
  return numeric.toFixed(1);
}

function drawHeroIcon(name, centerX, centerY, size, strokeStyle, lineWidth) {
  const path = HEROICON_PATHS[name];
  if (!path) {
    return;
  }

  const scale = size / 24;
  ctx.save();
  ctx.translate(centerX - size / 2, centerY - size / 2);
  ctx.scale(scale, scale);
  ctx.strokeStyle = strokeStyle;
  ctx.lineWidth = lineWidth / scale;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke(path);
  ctx.restore();
}

function fitArenaToView() {
  if (!mapState.arena) {
    return;
  }
  const padding = 36;
  const width = Math.max(1, canvas.clientWidth - padding * 2);
  const height = Math.max(1, canvas.clientHeight - padding * 2);
  const mapWidth = mapState.arena.size.width;
  const mapHeight = mapState.arena.size.height;
  const scale = Math.max(2, Math.min(width / mapWidth, height / mapHeight));
  mapState.transform.scale = scale;
  mapState.transform.offsetX = (canvas.clientWidth - mapWidth * scale) / 2;
  mapState.transform.offsetY = (canvas.clientHeight - mapHeight * scale) / 2;
}

function buildViewportKey(server, arena) {
  return `${server}:${arena.size.width}x${arena.size.height}`;
}

function worldToScreen(x, y) {
  return {
    x: mapState.transform.offsetX + x * mapState.transform.scale,
    y: mapState.transform.offsetY + y * mapState.transform.scale,
  };
}

function screenToWorld(x, y) {
  return {
    x: (x - mapState.transform.offsetX) / mapState.transform.scale,
    y: (y - mapState.transform.offsetY) / mapState.transform.scale,
  };
}

function screenToCell(x, y) {
  if (!mapState.arena) {
    return null;
  }
  const world = screenToWorld(x, y);
  const cell = {
    x: Math.floor(world.x),
    y: Math.floor(world.y),
  };
  if (
    cell.x < 0 ||
    cell.y < 0 ||
    cell.x >= mapState.arena.size.width ||
    cell.y >= mapState.arena.size.height
  ) {
    return null;
  }
  return cell;
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

function applyAlpha(hexColor, alpha) {
  const color = hexColor.replace("#", "");
  const red = Number.parseInt(color.slice(0, 2), 16);
  const green = Number.parseInt(color.slice(2, 4), 16);
  const blue = Number.parseInt(color.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}
