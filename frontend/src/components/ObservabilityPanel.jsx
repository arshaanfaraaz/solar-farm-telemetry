import { useEffect, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function Metric({ label, value, sub, highlight }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-xl font-bold font-mono ${highlight ?? 'text-white'}`}>{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function ObservabilityPanel() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    const load = () =>
      fetch(`${API_URL}/observability`)
        .then((r) => r.json())
        .then(setMetrics)
        .catch(() => {});

    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) return null;

  const fpColor =
    metrics.false_positive_rate_pct > 30 ? 'text-red-400' :
    metrics.false_positive_rate_pct > 10 ? 'text-yellow-400' :
    'text-green-400';

  const latencyColor =
    metrics.avg_alert_latency_ms > 3000 ? 'text-red-400' :
    metrics.avg_alert_latency_ms > 1500 ? 'text-yellow-400' :
    'text-cyan-400';

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <p className="text-xs text-gray-400 uppercase tracking-widest mb-3">
        Observability
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric
          label="Avg Alert Latency"
          value={`${metrics.avg_alert_latency_ms} ms`}
          sub="anomaly → incident"
          highlight={latencyColor}
        />
        <Metric
          label="False Positive Rate"
          value={`${metrics.false_positive_rate_pct}%`}
          sub={`${metrics.false_positive_count} of ${metrics.total_incidents}`}
          highlight={fpColor}
        />
        <Metric
          label="Avg LLM Cost"
          value={`$${metrics.avg_llm_cost_per_incident_usd}`}
          sub="per AI-analyzed incident"
          highlight="text-purple-400"
        />
        <Metric
          label="Total LLM Spend"
          value={`$${metrics.total_llm_cost_usd}`}
          sub={`${metrics.ai_analyzed_count} AI analyses`}
          highlight="text-purple-300"
        />
      </div>
    </div>
  );
}
