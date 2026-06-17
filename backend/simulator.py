import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class InverterStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class TelemetryReading:
    timestamp: str
    battery_temp: float        # °C
    battery_charge: float      # 0–100 %
    battery_health: float      # 0–100 %
    solar_output: float        # Watts
    sunlight_intensity: float  # 0–100 %
    voltage: float             # Volts
    current: float             # Amps
    inverter_status: InverterStatus
    inverter_efficiency: float # 0–100 %
    panel_id: str = "FARM-A"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "battery_temp": self.battery_temp,
            "battery_charge": self.battery_charge,
            "battery_health": self.battery_health,
            "solar_output": self.solar_output,
            "sunlight_intensity": self.sunlight_intensity,
            "voltage": self.voltage,
            "current": self.current,
            "inverter_status": self.inverter_status.value,
            "inverter_efficiency": self.inverter_efficiency,
            "panel_id": self.panel_id,
        }


class FaultMode(str, Enum):
    NONE = "none"
    OVERHEATING = "overheating"
    VOLTAGE_SPIKE = "voltage_spike"
    POWER_DROP = "power_drop"
    INVERTER_FAILURE = "inverter_failure"
    LOW_BATTERY = "low_battery"


class SolarFarmSimulator:
    """
    Simulates a realistic solar farm with time-of-day solar curves and
    probabilistic fault injection. Faults persist for FAULT_DURATION_TICKS
    ticks (~30 s at 2 s interval) so the anomaly engine can see sustained events.

    Solar output follows a Gaussian bell curve peaking at 13:00 local.
    Battery charge drifts based on solar fraction minus a constant load.
    """

    # Per-tick fault probabilities (low enough to feel like real events)
    _FAULT_PROBS: dict[FaultMode, float] = {
        FaultMode.OVERHEATING: 0.015,
        FaultMode.VOLTAGE_SPIKE: 0.010,
        FaultMode.POWER_DROP: 0.012,
        FaultMode.INVERTER_FAILURE: 0.008,
        FaultMode.LOW_BATTERY: 0.005,
    }
    FAULT_DURATION_TICKS = 15  # ~30 s

    def __init__(self) -> None:
        self._active_fault = FaultMode.NONE
        self._fault_ticks_left = 0
        self._battery_charge = 75.0
        self._battery_health = 94.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _solar_curve(self, hour: float) -> float:
        """Gaussian centred at 13:00, clipped to daylight hours (6–20)."""
        if hour < 6.0 or hour > 20.0:
            return 0.0
        return math.exp(-((hour - 13.0) ** 2) / (2 * 3.5 ** 2))

    def _noise(self, sigma: float) -> float:
        return random.gauss(0.0, sigma)

    def _tick_fault(self) -> None:
        """Advance fault state machine by one tick."""
        if self._active_fault != FaultMode.NONE:
            self._fault_ticks_left -= 1
            if self._fault_ticks_left <= 0:
                self._active_fault = FaultMode.NONE
            return

        for fault, prob in self._FAULT_PROBS.items():
            if random.random() < prob:
                self._active_fault = fault
                self._fault_ticks_left = self.FAULT_DURATION_TICKS
                break

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> TelemetryReading:
        self._tick_fault()

        now = datetime.now(timezone.utc)
        hour = now.hour + now.minute / 60.0
        sf = self._solar_curve(hour)  # 0–1 solar fraction

        sunlight = max(0.0, min(100.0, sf * 100 + self._noise(3.0)))
        solar = max(0.0, sf * 480 + self._noise(15.0))
        temp = 28.0 + sf * 12.0 + self._noise(1.5)
        voltage = 400.0 + self._noise(5.0)
        efficiency = max(0.0, min(100.0, 94.0 + self._noise(1.0)))
        inverter = InverterStatus.ONLINE

        # Battery charge drifts: solar charges, load discharges
        charge_delta = (sf * 0.4 - 0.15) + self._noise(0.05)
        self._battery_charge = max(5.0, min(100.0, self._battery_charge + charge_delta))

        # Apply active fault
        match self._active_fault:
            case FaultMode.OVERHEATING:
                temp += 18.0 + self._noise(2.0)
            case FaultMode.VOLTAGE_SPIKE:
                voltage += 55.0 + self._noise(5.0)
            case FaultMode.POWER_DROP:
                solar *= 0.15
                sunlight *= 0.25
            case FaultMode.INVERTER_FAILURE:
                inverter = InverterStatus.OFFLINE
                efficiency = 0.0
                solar = 0.0
            case FaultMode.LOW_BATTERY:
                self._battery_charge = max(3.0, self._battery_charge - 25.0)

        # Thermal degradation of inverter at high temps
        if temp > 45:
            efficiency = max(60.0, efficiency - (temp - 45) * 1.5)
            if inverter == InverterStatus.ONLINE and temp > 50:
                inverter = InverterStatus.DEGRADED

        current = solar / voltage if voltage > 0 else 0.0

        return TelemetryReading(
            timestamp=now.isoformat(),
            battery_temp=round(temp, 1),
            battery_charge=round(self._battery_charge, 1),
            battery_health=round(self._battery_health, 1),
            solar_output=round(solar, 1),
            sunlight_intensity=round(sunlight, 1),
            voltage=round(voltage, 1),
            current=round(current, 2),
            inverter_status=inverter,
            inverter_efficiency=round(efficiency, 1),
        )
