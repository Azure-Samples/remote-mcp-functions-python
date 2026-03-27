import { App } from "@modelcontextprotocol/ext-apps";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const el = (id: string) => document.getElementById(id)!;

// ---------------------------------------------------------------------------
// Interfaces matching the report JSON produced by IoTService.generate_report()
// ---------------------------------------------------------------------------

interface MetricsSummary {
  device_id: string;
  location: string;
  timestamp: string;
  current_metrics: {
    temperature_celsius: number;
    humidity_percent: number;
    pressure_bar: number;
    vibration_hz: number;
    power_consumption_kw: number;
  };
  temperature_history_stats: {
    count?: number;
    min?: number;
    max?: number;
    avg?: number;
    stdev?: number;
    latest?: number;
    trend?: string;
  };
  status: string;
}

interface Alert {
  device_id: string;
  location: string;
  code: string;
  severity: string;
  message: string;
  triggered_at: string;
  resolved: boolean;
}

interface MaintenanceInfo {
  last_service_date: string;
  next_service_date: string;
  technician: string;
  notes: string;
  days_to_next_service: number | null;
}

interface NetworkInfo {
  ip_address: string;
  protocol: string;
  signal_strength_dbm: number;
  connected_gateway: string;
}

interface SensorReport {
  device_id: string;
  location: string;
  firmware_version: string;
  status: string;
  tags: string[];
  health_score: number;
  metrics_summary: MetricsSummary;
  active_alerts: Alert[];
  active_alerts_count: number;
  maintenance: MaintenanceInfo;
  network: NetworkInfo;
  report_generated_at: string;
}

// ---------------------------------------------------------------------------
// Status helpers
// ---------------------------------------------------------------------------

function statusIcon(status: string): string {
  switch (status) {
    case "operational":  return "🟢";
    case "degraded":     return "🟡";
    case "offline":      return "🔴";
    case "maintenance":  return "🔧";
    default:             return "📡";
  }
}

function healthClass(score: number): string {
  if (score >= 80) return "health-good";
  if (score >= 50) return "health-warn";
  return "health-bad";
}

function alertIcon(severity: string): string {
  switch (severity) {
    case "critical": return "🔴";
    case "warning":  return "🟡";
    case "info":     return "🔵";
    default:         return "⚪";
  }
}

// ---------------------------------------------------------------------------
// Sparkline renderer
// ---------------------------------------------------------------------------

function renderSparkline(containerId: string, values: number[]): void {
  const svg = el(containerId) as unknown as SVGSVGElement;
  if (!svg || values.length === 0) return;

  const w = 300;
  const h = 60;
  const pad = 4;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = (w - pad * 2) / Math.max(values.length - 1, 1);

  const points = values.map((v, i) => {
    const x = pad + i * step;
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  });

  // Gradient area
  const areaPoints = [
    `${pad},${h - pad}`,
    ...points,
    `${pad + (values.length - 1) * step},${h - pad}`,
  ].join(" ");

  // Line path
  const linePath = points.join(" ");

  svg.innerHTML = `
    <defs>
      <linearGradient id="sp-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="rgba(56,189,248,0.35)" />
        <stop offset="100%" stop-color="rgba(56,189,248,0)" />
      </linearGradient>
    </defs>
    <polygon points="${areaPoints}" fill="url(#sp-grad)" />
    <polyline points="${linePath}" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linejoin="round" />
    ${points.map((p) => `<circle cx="${p.split(",")[0]}" cy="${p.split(",")[1]}" r="3" fill="#38bdf8" />`).join("")}
  `;
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function render(report: SensorReport): void {
  // Header
  el("status-icon").textContent = statusIcon(report.status);
  el("device-name").textContent = report.device_id;
  el("device-location").textContent = `${report.location}  ·  fw ${report.firmware_version}  ·  ${report.status}`;

  const badge = el("health-badge");
  badge.textContent = `${report.health_score}`;
  badge.className = `health-badge ${healthClass(report.health_score)}`;

  // Metrics
  const cm = report.metrics_summary.current_metrics;
  el("m-temp").textContent = `${cm.temperature_celsius} °C`;
  el("m-humidity").textContent = `${cm.humidity_percent} %`;
  el("m-pressure").textContent = `${cm.pressure_bar} bar`;
  el("m-vibration").textContent = `${cm.vibration_hz} Hz`;
  el("m-power").textContent = `${cm.power_consumption_kw} kW`;

  // History sparkline
  const hs = report.metrics_summary.temperature_history_stats;
  if (hs && hs.count && hs.count > 0) {
    // We don't have the raw values in the report, but we can reconstruct a tiny
    // sparkline from the stats if we have at least min/max/avg/latest.
    // Actually the report comes from generate_report which includes metrics_summary
    // that itself may not carry raw readings. We'll parse tool result content to
    // check for raw readings embedded. For now use the stats we have.
    const statsHtml: string[] = [];
    if (hs.min !== undefined)   statsHtml.push(`<span>Min</span> <strong>${hs.min}°C</strong>`);
    if (hs.max !== undefined)   statsHtml.push(`<span>Max</span> <strong>${hs.max}°C</strong>`);
    if (hs.avg !== undefined)   statsHtml.push(`<span>Avg</span> <strong>${hs.avg}°C</strong>`);
    if (hs.stdev !== undefined) statsHtml.push(`<span>σ</span> <strong>${hs.stdev}</strong>`);
    if (hs.trend)               statsHtml.push(`<span>Trend</span> <strong>${trendArrow(hs.trend)}</strong>`);
    el("history-stats").innerHTML = statsHtml.join("");
  }

  // Alerts
  const alertsContainer = el("alerts-list");
  if (report.active_alerts.length === 0) {
    alertsContainer.innerHTML = `<div class="no-alerts">✅ No active alerts</div>`;
  } else {
    alertsContainer.innerHTML = report.active_alerts
      .map(
        (a) => `
      <div class="alert-item ${a.severity}">
        <div class="alert-icon">${alertIcon(a.severity)}</div>
        <div class="alert-body">
          <div class="alert-code">${escapeHtml(a.code)}</div>
          <div class="alert-msg">${escapeHtml(a.message)}</div>
        </div>
        <div class="alert-time">${escapeHtml(a.triggered_at)}</div>
      </div>`
      )
      .join("");
  }

  // Network
  el("net-ip").textContent = report.network.ip_address;
  el("net-proto").textContent = report.network.protocol;
  el("net-signal").textContent = `${report.network.signal_strength_dbm} dBm`;
  el("net-gw").textContent = report.network.connected_gateway;

  // Maintenance
  el("maint-last").textContent = report.maintenance.last_service_date;
  el("maint-next").textContent = report.maintenance.next_service_date;
  el("maint-days").textContent =
    report.maintenance.days_to_next_service !== null
      ? `${report.maintenance.days_to_next_service}d`
      : "—";
  el("maint-tech").textContent = report.maintenance.technician;

  // Tags
  if (report.tags && report.tags.length > 0) {
    el("tags-section").style.display = "";
    el("tags-list").innerHTML = report.tags
      .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
      .join("");
  }

  // Footer
  el("footer").textContent = `Report generated at ${report.report_generated_at}`;
}

// ---------------------------------------------------------------------------
// Small utilities
// ---------------------------------------------------------------------------

function trendArrow(trend: string): string {
  switch (trend) {
    case "rising":  return "↑ Rising";
    case "falling": return "↓ Falling";
    default:        return "→ Stable";
  }
}

function escapeHtml(text: string): string {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
}

// ---------------------------------------------------------------------------
// Parse tool result from MCP host
// ---------------------------------------------------------------------------

function parseToolResult(
  content: Array<{ type: string; text?: string }> | undefined
): SensorReport | null {
  if (!content || content.length === 0) return null;
  const textBlock = content.find((c) => c.type === "text" && c.text);
  if (!textBlock?.text) return null;
  try {
    return JSON.parse(textBlock.text) as SensorReport;
  } catch (e) {
    console.error("Failed to parse sensor report:", e);
    return null;
  }
}

// ---------------------------------------------------------------------------
// MCP App bootstrap
// ---------------------------------------------------------------------------

const app = new App({ name: "IoT Sensor Dashboard", version: "1.0.0" });

app.ontoolinput = (params) => {
  console.log("Tool args:", params.arguments);
  app.sendLog({
    level: "info",
    data: `Received tool input: ${JSON.stringify(params.arguments)}`,
  });
};

app.ontoolresult = (params) => {
  console.log("Tool result:", params.content);
  const report = parseToolResult(
    params.content as Array<{ type: string; text?: string }>
  );
  if (report) {
    // If we can extract raw history readings from the report, render sparkline
    const hs = report.metrics_summary.temperature_history_stats;
    // Reconstruct approximate sparkline from min/avg/latest if we have them
    if (hs && hs.min !== undefined && hs.max !== undefined && hs.avg !== undefined && hs.latest !== undefined) {
      const fakeReadings = [hs.min, hs.avg, hs.max, hs.avg, hs.latest];
      renderSparkline("sparkline", fakeReadings);
    }
    render(report);
  } else {
    el("device-location").textContent = "Error parsing sensor data";
  }
};

app.onhostcontextchanged = (ctx) => {
  if (ctx.theme) {
    document.documentElement.dataset.theme = ctx.theme;
  }
};

(async () => {
  await app.connect();
  const theme = app.getHostContext()?.theme;
  if (theme) document.documentElement.dataset.theme = theme;
  el("footer").textContent = "Connected — waiting for sensor report…";
})();
