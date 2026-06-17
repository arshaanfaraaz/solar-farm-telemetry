import time
from dataclasses import dataclass, field
from typing import Optional

from ai_analysis import AIAnalysis
from anomaly import Anomaly, Severity
from simulator import TelemetryReading


@dataclass
class Incident:
    id: str
    timestamp: str
    severity: str
    issue: str
    anomalies: list[dict]
    telemetry_snapshot: dict
    ai_analysis: Optional[dict]
    acknowledged: bool = False
    resolved: bool = False
    false_positive: bool = False
    alert_latency_ms: Optional[int] = None
    llm_cost_usd: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "issue": self.issue,
            "anomalies": self.anomalies,
            "telemetry_snapshot": self.telemetry_snapshot,
            "ai_analysis": self.ai_analysis,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "false_positive": self.false_positive,
            "alert_latency_ms": self.alert_latency_ms,
            "llm_cost_usd": self.llm_cost_usd,
        }


class IncidentStore:
    """
    In-memory incident log with two guard-rails:

    1. Severity-aware deduplication — the same anomaly type combination
       won't produce a new incident within COOLDOWN_SECONDS (default 5 min).

    2. Bounded size — oldest incidents are evicted once MAX_INCIDENTS is
       reached, preventing unbounded memory growth in long-running processes.
    """

    MAX_INCIDENTS = 100
    COOLDOWN_SECONDS = 300

    _SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]

    def __init__(self) -> None:
        self._incidents: list[Incident] = []
        self._last_seen: dict[str, float] = {}
        self._counter = 0

    def _key(self, anomalies: list[Anomaly]) -> str:
        return ",".join(sorted(a.type.value for a in anomalies))

    def _is_duplicate(self, anomalies: list[Anomaly]) -> bool:
        return (time.monotonic() - self._last_seen.get(self._key(anomalies), 0.0)) < self.COOLDOWN_SECONDS

    def _max_severity(self, anomalies: list[Anomaly]) -> str:
        present = {a.severity for a in anomalies}
        for sev in reversed(self._SEVERITY_ORDER):
            if sev in present:
                return sev.value
        return Severity.LOW.value

    def create(
        self,
        reading: TelemetryReading,
        anomalies: list[Anomaly],
        analysis: Optional[AIAnalysis],
        alert_latency_ms: Optional[int] = None,
    ) -> Optional["Incident"]:
        if not anomalies or self._is_duplicate(anomalies):
            return None

        self._counter += 1
        incident = Incident(
            id=f"INC-{self._counter:04d}",
            timestamp=reading.timestamp,
            severity=self._max_severity(anomalies),
            issue=(analysis.issue if analysis
                   else anomalies[0].type.value.replace("_", " ").title()),
            anomalies=[a.to_dict() for a in anomalies],
            telemetry_snapshot={
                "battery_temp": reading.battery_temp,
                "battery_charge": reading.battery_charge,
                "solar_output": reading.solar_output,
                "voltage": reading.voltage,
                "inverter_status": reading.inverter_status.value,
            },
            ai_analysis=analysis.to_dict() if analysis else None,
            alert_latency_ms=alert_latency_ms,
            llm_cost_usd=analysis.llm_cost_usd if analysis else None,
        )

        self._last_seen[self._key(anomalies)] = time.monotonic()

        if len(self._incidents) >= self.MAX_INCIDENTS:
            self._incidents.pop(0)
        self._incidents.append(incident)
        return incident

    def get_all(self) -> list[Incident]:
        return list(reversed(self._incidents))

    def acknowledge(self, incident_id: str) -> bool:
        for inc in self._incidents:
            if inc.id == incident_id:
                inc.acknowledged = True
                return True
        return False

    def resolve(self, incident_id: str) -> bool:
        for inc in self._incidents:
            if inc.id == incident_id:
                inc.resolved = True
                return True
        return False

    def mark_false_positive(self, incident_id: str) -> bool:
        for inc in self._incidents:
            if inc.id == incident_id:
                inc.false_positive = True
                return True
        return False

    def delete(self, incident_id: str) -> bool:
        before = len(self._incidents)
        self._incidents = [i for i in self._incidents if i.id != incident_id]
        return len(self._incidents) < before

    def observability_stats(self) -> dict:
        incidents = self._incidents
        total = len(incidents)
        fp_count = sum(1 for i in incidents if i.false_positive)
        fp_rate = round(fp_count / total * 100, 1) if total else 0.0

        ai_incidents = [i for i in incidents if i.llm_cost_usd is not None]
        total_cost = sum(i.llm_cost_usd for i in ai_incidents)
        avg_cost = total_cost / len(ai_incidents) if ai_incidents else 0.0

        latencies = [i.alert_latency_ms for i in incidents if i.alert_latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return {
            "total_incidents": total,
            "false_positive_count": fp_count,
            "false_positive_rate_pct": fp_rate,
            "ai_analyzed_count": len(ai_incidents),
            "total_llm_cost_usd": round(total_cost, 6),
            "avg_llm_cost_per_incident_usd": round(avg_cost, 6),
            "avg_alert_latency_ms": round(avg_latency, 1),
        }
