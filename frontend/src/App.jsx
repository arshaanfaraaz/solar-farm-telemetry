import { useEffect, useState } from 'react';
import Header from './components/Header';
import IncidentPanel from './components/IncidentPanel';
import LiveChart from './components/LiveChart';
import MetricCard from './components/MetricCard';
import ObservabilityPanel from './components/ObservabilityPanel';
import { useWebSocket } from './hooks/useWebSocket';

const MAX_HISTORY = 40;

// Find the worst anomaly of a given type keyword in the anomaly list
function findAnomaly(anomalies, typeKeyword) {
  return anomalies.find((a) => a.type.includes(typeKeyword)) ?? null;
}

export default function App() {
  const { data, connected, incidents } = useWebSocket();

  // Rolling time-series — last MAX_HISTORY points per metric
  const [history, setHistory] = useState({
    solar:   [],
    temp:    [],
    voltage: [],
    charge:  [],
  });

  useEffect(() => {
    if (!data?.telemetry) return;
    const t = data.telemetry;
    const ts = new Date(t.timestamp).toLocaleTimeString([], {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });

    setHistory((prev) => ({
      solar:   [...prev.solar,   { time: ts, value: t.solar_output }].slice(-MAX_HISTORY),
      temp:    [...prev.temp,    { time: ts, value: t.battery_temp }].slice(-MAX_HISTORY),
      voltage: [...prev.voltage, { time: ts, value: t.voltage }].slice(-MAX_HISTORY),
      charge:  [...prev.charge,  { time: ts, value: t.battery_charge }].slice(-MAX_HISTORY),
    }));
  }, [data]);

  const t = data?.telemetry ?? null;
  const anomalies = data?.anomalies ?? [];

  const tempAnomaly    = findAnomaly(anomalies, 'BATTERY_OVERHEAT');
  const chargeAnomaly  = findAnomaly(anomalies, 'BATTERY_LOW_CHARGE');
  const voltageAnomaly = findAnomaly(anomalies, 'VOLTAGE');
  const powerAnomaly   = findAnomaly(anomalies, 'POWER_DROP');
  const inverterAnomaly = findAnomaly(anomalies, 'INVERTER');

  const inverterStatus = t?.inverter_status ?? 'unknown';
  const inverterColor =
    inverterStatus === 'online'   ? 'text-green-400' :
    inverterStatus === 'degraded' ? 'text-yellow-400' :
    'text-red-400';

  return (
    <div className="min-h-screen bg-gray-950">
      <Header
        connected={connected}
        timestamp={t?.timestamp}
        anomalyCount={anomalies.length}
      />

      <div className="p-4 space-y-4 max-w-7xl mx-auto">

        {/* === Metric Cards === */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          <MetricCard
            label="Battery Temp"
            value={t?.battery_temp}
            unit="°C"
            icon="🌡"
            anomalySeverity={tempAnomaly?.severity}
            anomalyMsg={tempAnomaly?.message}
            subtext="nominal < 42 °C"
          />
          <MetricCard
            label="Battery Charge"
            value={t?.battery_charge}
            unit="%"
            icon="🔋"
            anomalySeverity={chargeAnomaly?.severity}
            anomalyMsg={chargeAnomaly?.message}
            subtext={`health ${t?.battery_health ?? '—'}%`}
          />
          <MetricCard
            label="Solar Output"
            value={t?.solar_output}
            unit="W"
            icon="☀"
            anomalySeverity={powerAnomaly?.severity}
            anomalyMsg={powerAnomaly?.message}
            subtext={`sunlight ${t?.sunlight_intensity ?? '—'}%`}
          />
          <MetricCard
            label="Voltage"
            value={t?.voltage}
            unit="V"
            icon="⚡"
            anomalySeverity={voltageAnomaly?.severity}
            anomalyMsg={voltageAnomaly?.message}
            subtext="nominal 395–405 V"
          />
          {/* Inverter card */}
          <div className={`rounded-lg p-4 bg-gray-900 ${
            inverterAnomaly
              ? 'ring-1 ' + (inverterAnomaly.severity === 'CRITICAL' ? 'ring-red-500 bg-red-950/20'
                            : 'ring-orange-500 bg-orange-950/20')
              : ''
          }`}>
            <div className="flex items-start justify-between mb-3">
              <span className="text-gray-400 text-xs uppercase tracking-widest">Inverter</span>
              <span className="text-lg">🔌</span>
            </div>
            <div className={`text-xl font-bold uppercase tracking-wider mb-1 ${inverterColor}`}>
              {inverterStatus}
            </div>
            <p className="text-xs text-gray-500">
              efficiency {t?.inverter_efficiency ?? '—'}%
            </p>
            {inverterAnomaly && (
              <p className={`text-xs mt-1 ${
                inverterAnomaly.severity === 'CRITICAL' ? 'text-red-400' : 'text-orange-400'
              }`}>{inverterAnomaly.message}</p>
            )}
          </div>
        </div>

        {/* === Charts === */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <LiveChart
            title="Solar Output (W)"
            data={history.solar}
            unit="W"
            color="#facc15"
            warnLine={50}
            domain={[0, 520]}
          />
          <LiveChart
            title="Battery Temp (°C)"
            data={history.temp}
            unit="°C"
            color="#f97316"
            warnLine={42}
            critLine={52}
            domain={[20, 70]}
          />
          <LiveChart
            title="Voltage (V)"
            data={history.voltage}
            unit="V"
            color="#22d3ee"
            warnLine={440}
            domain={[350, 480]}
          />
        </div>

        {/* Battery charge chart — full width */}
        <LiveChart
          title="Battery Charge (%)"
          data={history.charge}
          unit="%"
          color="#34d399"
          warnLine={15}
          critLine={5}
          domain={[0, 105]}
        />

        {/* === Observability Panel === */}
        <ObservabilityPanel />

        {/* === Incident Panel === */}
        <IncidentPanel incidents={incidents} />
      </div>
    </div>
  );
}
