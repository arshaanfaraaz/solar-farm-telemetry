from dataclasses import dataclass
from enum import Enum

from simulator import InverterStatus, TelemetryReading


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyType(str, Enum):
    BATTERY_OVERHEAT = "BATTERY_OVERHEAT"
    BATTERY_LOW_CHARGE = "BATTERY_LOW_CHARGE"
    VOLTAGE_HIGH = "VOLTAGE_HIGH"
    VOLTAGE_LOW = "VOLTAGE_LOW"
    POWER_DROP = "POWER_DROP"
    INVERTER_OFFLINE = "INVERTER_OFFLINE"
    INVERTER_DEGRADED = "INVERTER_DEGRADED"
    EFFICIENCY_LOW = "EFFICIENCY_LOW"


@dataclass
class Anomaly:
    type: AnomalyType
    severity: Severity
    message: str
    value: float
    threshold: float

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
        }


class AnomalyDetector:
    """
    Threshold-based anomaly detector. Pure rule engine — no ML inference,
    zero latency, fully auditable. This is how industrial SCADA systems
    start; ML layers are added on top, not instead of, rule engines.

    All thresholds are calibrated against the simulator's nominal ranges:
      battery_temp nominal: 28–40 °C
      voltage nominal:      395–405 V
      solar nominal:        0–480 W depending on hour
      efficiency nominal:   93–95 %
    """

    def detect(self, reading: TelemetryReading) -> list[Anomaly]:
        found: list[Anomaly] = []

        # --- Battery temperature ---
        if reading.battery_temp >= 52:
            found.append(Anomaly(
                AnomalyType.BATTERY_OVERHEAT, Severity.CRITICAL,
                f"Battery temperature critical at {reading.battery_temp}°C",
                reading.battery_temp, 52,
            ))
        elif reading.battery_temp >= 46:
            found.append(Anomaly(
                AnomalyType.BATTERY_OVERHEAT, Severity.HIGH,
                f"Battery overheating: {reading.battery_temp}°C",
                reading.battery_temp, 46,
            ))
        elif reading.battery_temp >= 42:
            found.append(Anomaly(
                AnomalyType.BATTERY_OVERHEAT, Severity.LOW,
                f"Battery temperature elevated: {reading.battery_temp}°C",
                reading.battery_temp, 42,
            ))

        # --- Battery charge ---
        if reading.battery_charge <= 5:
            found.append(Anomaly(
                AnomalyType.BATTERY_LOW_CHARGE, Severity.CRITICAL,
                f"Battery critically depleted: {reading.battery_charge}%",
                reading.battery_charge, 5,
            ))
        elif reading.battery_charge <= 15:
            found.append(Anomaly(
                AnomalyType.BATTERY_LOW_CHARGE, Severity.HIGH,
                f"Battery low: {reading.battery_charge}%",
                reading.battery_charge, 15,
            ))

        # --- Voltage high ---
        if reading.voltage >= 460:
            found.append(Anomaly(
                AnomalyType.VOLTAGE_HIGH, Severity.CRITICAL,
                f"Voltage surge: {reading.voltage}V (limit 460V)",
                reading.voltage, 460,
            ))
        elif reading.voltage >= 440:
            found.append(Anomaly(
                AnomalyType.VOLTAGE_HIGH, Severity.HIGH,
                f"Voltage spike: {reading.voltage}V",
                reading.voltage, 440,
            ))

        # --- Voltage low ---
        if reading.voltage <= 355:
            found.append(Anomaly(
                AnomalyType.VOLTAGE_LOW, Severity.HIGH,
                f"Voltage critically low: {reading.voltage}V",
                reading.voltage, 355,
            ))
        elif reading.voltage <= 370:
            found.append(Anomaly(
                AnomalyType.VOLTAGE_LOW, Severity.MEDIUM,
                f"Voltage below nominal: {reading.voltage}V",
                reading.voltage, 370,
            ))

        # --- Power drop (only meaningful during daylight) ---
        if reading.sunlight_intensity > 20 and reading.solar_output < 50:
            found.append(Anomaly(
                AnomalyType.POWER_DROP, Severity.HIGH,
                f"Power drop during {reading.sunlight_intensity:.0f}% sunlight: {reading.solar_output}W",
                reading.solar_output, 50,
            ))

        # --- Inverter ---
        if reading.inverter_status == InverterStatus.OFFLINE:
            found.append(Anomaly(
                AnomalyType.INVERTER_OFFLINE, Severity.CRITICAL,
                "Inverter offline — power conversion halted",
                0, 1,
            ))
        elif reading.inverter_status == InverterStatus.DEGRADED:
            found.append(Anomaly(
                AnomalyType.INVERTER_DEGRADED, Severity.HIGH,
                f"Inverter degraded: {reading.inverter_efficiency}% efficiency",
                reading.inverter_efficiency, 80,
            ))

        # --- Efficiency (online inverters only, avoids double-reporting) ---
        if (reading.inverter_status == InverterStatus.ONLINE
                and reading.inverter_efficiency < 80):
            found.append(Anomaly(
                AnomalyType.EFFICIENCY_LOW, Severity.MEDIUM,
                f"Inverter efficiency low: {reading.inverter_efficiency}%",
                reading.inverter_efficiency, 80,
            ))

        return found
