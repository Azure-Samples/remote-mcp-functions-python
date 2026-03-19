"""IoT Service - Models and analysis logic for data coming from industrial sensors."""

import json
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class AlertModel:
    """A single alert emitted by the sensor."""

    code: str
    severity: str
    message: str
    triggered_at: str
    resolved: bool = False

    def __post_init__(self) -> None:
        allowed = {"info", "warning", "critical"}
        if self.severity not in allowed:
            raise ValueError(f"'severity' must be one of {allowed}, got: '{self.severity}'")


@dataclass
class MetricsModel:
    """Physical measurements detected by the sensor at the current instant."""

    temperature_celsius: float
    humidity_percent: float
    pressure_bar: float
    vibration_hz: float
    power_consumption_kw: float

    def __post_init__(self) -> None:
        if self.temperature_celsius < -273.15:
            raise ValueError("Temperature cannot be below absolute zero")
        if not (0 <= self.humidity_percent <= 100):
            raise ValueError("humidity_percent must be between 0 and 100")
        if self.pressure_bar <= 0:
            raise ValueError("pressure_bar must be greater than 0")
        if self.vibration_hz < 0:
            raise ValueError("vibration_hz must be >= 0")
        if self.power_consumption_kw < 0:
            raise ValueError("power_consumption_kw must be >= 0")
        self.temperature_celsius = round(self.temperature_celsius, 2)


@dataclass
class MaintenanceInfoModel:
    """Information about the last and next scheduled maintenance of the device."""

    last_service_date: str
    next_service_date: str
    technician: str
    notes: str = ""

    def __post_init__(self) -> None:
        try:
            last = datetime.strptime(self.last_service_date, "%Y-%m-%d")
            nxt = datetime.strptime(self.next_service_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Dates must be in YYYY-MM-DD format")
        if nxt <= last:
            raise ValueError("next_service_date must be later than last_service_date")


@dataclass
class NetworkInfoModel:
    """Network and connectivity information for the device."""

    ip_address: str
    protocol: str
    signal_strength_dbm: int
    connected_gateway: str

    def __post_init__(self) -> None:
        if self.signal_strength_dbm > 0:
            raise ValueError("signal_strength_dbm must be <= 0 (negative dBm value)")
        if self.signal_strength_dbm < -120:
            raise ValueError("signal_strength_dbm cannot be lower than -120 dBm")


@dataclass
class SensorPayload:
    """Full payload structure sent by an industrial IoT sensor.

    Example of a valid JSON payload::

        {
            "device_id": "sensor-industrial-001",
            "location": "Plant-A / Zone-3 / Line-2",
            "timestamp": "2026-03-19T10:30:00Z",
            "firmware_version": "2.4.1",
            "status": "operational",
            "tags": ["critical", "monitored", "area-b"],
            "metrics": {
                "temperature_celsius": 72.4,
                "humidity_percent": 45.2,
                "pressure_bar": 3.15,
                "vibration_hz": 120.8,
                "power_consumption_kw": 18.7
            },
            "alerts": [
                {
                    "code": "TEMP_HIGH",
                    "severity": "warning",
                    "message": "Temperature above threshold",
                    "triggered_at": "2026-03-19T10:28:00Z"
                }
            ],
            "maintenance": {
                "last_service_date": "2025-12-01",
                "next_service_date": "2026-06-01",
                "technician": "Mario Rossi",
                "notes": "Replaced filter unit B"
            },
            "network": {
                "ip_address": "192.168.10.45",
                "protocol": "MQTT",
                "signal_strength_dbm": -67,
                "connected_gateway": "gw-plant-a-01"
            },
            "history_last_5_readings": [71.2, 71.8, 72.0, 72.1, 72.4]
        }
    """

    device_id: str
    location: str
    timestamp: str
    firmware_version: str
    status: str
    metrics: MetricsModel
    maintenance: MaintenanceInfoModel
    network: NetworkInfoModel
    tags: List[str] = field(default_factory=list)
    alerts: List[AlertModel] = field(default_factory=list)
    history_last_5_readings: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ValueError("device_id must not be empty")
        if not self.location:
            raise ValueError("location must not be empty")
        allowed_statuses = {"operational", "degraded", "offline", "maintenance"}
        if self.status not in allowed_statuses:
            raise ValueError(f"'status' must be one of {allowed_statuses}, got: '{self.status}'")
        if len(self.history_last_5_readings) > 10:
            raise ValueError("history_last_5_readings can contain at most 10 values")
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"timestamp '{self.timestamp}' is not a valid ISO 8601 format")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# ---------------------------------------------------------------------------
# IoT Service
# ---------------------------------------------------------------------------

class IoTService:
    """Service for validating and analysing payloads from IoT sensors."""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_payload(self, data: Dict[str, Any]) -> SensorPayload:
        """Validate a raw dictionary and convert it into a SensorPayload.

        Raises ``ValueError`` if any field is missing or invalid.
        """
        metrics = MetricsModel(**data["metrics"])
        maintenance = MaintenanceInfoModel(**data["maintenance"])
        network = NetworkInfoModel(**data["network"])
        alerts = [AlertModel(**a) for a in data.get("alerts", [])]

        return SensorPayload(
            device_id=data["device_id"],
            location=data["location"],
            timestamp=data["timestamp"],
            firmware_version=data["firmware_version"],
            status=data["status"],
            tags=data.get("tags", []),
            metrics=metrics,
            alerts=alerts,
            maintenance=maintenance,
            network=network,
            history_last_5_readings=data.get("history_last_5_readings", []),
        )

    # ------------------------------------------------------------------
    # Metrics analysis
    # ------------------------------------------------------------------

    def get_metrics_summary(self, payload: SensorPayload) -> Dict[str, Any]:
        """Return a summary of the current metrics and a statistical analysis
        of the temperature reading history."""

        history = payload.history_last_5_readings

        history_stats: Dict[str, Any] = {}
        if history:
            history_stats = {
                "count": len(history),
                "min": round(min(history), 2),
                "max": round(max(history), 2),
                "avg": round(statistics.mean(history), 2),
                "stdev": round(statistics.stdev(history), 2) if len(history) > 1 else 0.0,
                "latest": history[-1],
                "trend": (
                    "rising"
                    if len(history) >= 2 and history[-1] > history[-2]
                    else "falling"
                    if len(history) >= 2 and history[-1] < history[-2]
                    else "stable"
                ),
            }

        return {
            "device_id": payload.device_id,
            "location": payload.location,
            "timestamp": payload.timestamp,
            "current_metrics": asdict(payload.metrics),
            "temperature_history_stats": history_stats,
            "status": payload.status,
        }

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def get_active_alerts(self, payload: SensorPayload) -> List[Dict[str, Any]]:
        """Return unresolved alerts, enriched with device_id and location."""
        return [
            {
                "device_id": payload.device_id,
                "location": payload.location,
                **asdict(alert),
            }
            for alert in payload.alerts
            if not alert.resolved
        ]

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------

    def generate_report(self, payload: SensorPayload) -> Dict[str, Any]:
        """Generate a full device report with health score, metrics,
        active alerts, and network and maintenance information."""

        active_alerts = self.get_active_alerts(payload)
        metrics_summary = self.get_metrics_summary(payload)

        # Health score: starts at 100, decremented by degraded status and active alerts
        health_score = 100
        status_penalties = {
            "degraded": 20,
            "offline": 60,
            "maintenance": 10,
        }
        health_score -= status_penalties.get(payload.status, 0)

        severity_penalties = {"critical": 20, "warning": 10, "info": 2}
        for alert in active_alerts:
            health_score -= severity_penalties.get(alert.get("severity", "info"), 0)

        health_score = max(0, health_score)

        # Days until next scheduled maintenance
        days_to_maintenance: Optional[int] = None
        try:
            next_svc = datetime.strptime(
                payload.maintenance.next_service_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            days_to_maintenance = (next_svc - now).days
        except Exception:
            pass

        return {
            "device_id": payload.device_id,
            "location": payload.location,
            "firmware_version": payload.firmware_version,
            "status": payload.status,
            "tags": payload.tags,
            "health_score": health_score,
            "metrics_summary": metrics_summary,
            "active_alerts": active_alerts,
            "active_alerts_count": len(active_alerts),
            "maintenance": {
                **asdict(payload.maintenance),
                "days_to_next_service": days_to_maintenance,
            },
            "network": asdict(payload.network),
            "report_generated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
