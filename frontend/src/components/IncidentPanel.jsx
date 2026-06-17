import { useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const SEV_STYLES = {
  CRITICAL: { badge: 'bg-red-900 text-red-300 border border-red-700',         dot: 'bg-red-500' },
  HIGH:     { badge: 'bg-orange-900 text-orange-300 border border-orange-700', dot: 'bg-orange-500' },
  MEDIUM:   { badge: 'bg-yellow-900 text-yellow-300 border border-yellow-700', dot: 'bg-yellow-500' },
  LOW:      { badge: 'bg-gray-800 text-gray-400 border border-gray-600',       dot: 'bg-gray-500' },
};

const ACTION_STYLES = {
  escalate: 'bg-red-900/50 text-red-300 border border-red-700',
  notify:   'bg-orange-900/50 text-orange-300 border border-orange-700',
  monitor:  'bg-gray-800 text-gray-400 border border-gray-600',
};

function IncidentRow({ incident }) {
  const [open, setOpen] = useState(false);
  const [isFP, setIsFP] = useState(incident.false_positive);
  const sev = SEV_STYLES[incident.severity] ?? SEV_STYLES.LOW;
  const ts = new Date(incident.timestamp).toLocaleTimeString([], {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  const handleFalsePositive = async (e) => {
    e.stopPropagation();
    try {
      await fetch(`${API_URL}/incidents/${incident.id}/false-positive`, { method: 'POST' });
      setIsFP(true);
    } catch (_) {}
  };

  const action = incident.ai_analysis?.action;

  return (
    <div className={`rounded-lg border border-gray-800 mb-2 overflow-hidden ${
      incident.resolved || isFP ? 'opacity-40' : ''
    }`}>
      {/* Row header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full text-left flex items-center gap-3 px-4 py-3 hover:bg-gray-800 transition-colors"
      >
        <span className={`w-2 h-2 rounded-full shrink-0 ${sev.dot}`} />
        <span className={`text-xs font-bold px-2 py-0.5 rounded ${sev.badge}`}>
          {incident.severity}
        </span>
        {action && (
          <span className={`text-xs px-2 py-0.5 rounded uppercase tracking-widest ${ACTION_STYLES[action] ?? ACTION_STYLES.monitor}`}>
            {action}
          </span>
        )}
        <span className="flex-1 text-sm text-white truncate">{incident.issue}</span>
        {incident.alert_latency_ms != null && (
          <span className="text-xs text-gray-600 shrink-0">{incident.alert_latency_ms}ms</span>
        )}
        <span className="text-xs text-gray-500 shrink-0">{ts}</span>
        <span className="text-gray-600 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="px-4 pb-4 border-t border-gray-800 pt-3 bg-gray-950">
          {/* Anomaly tags */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            {incident.anomalies.map((a, i) => (
              <span key={i} className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">
                {a.type}
              </span>
            ))}
          </div>

          {/* Telemetry snapshot */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            {Object.entries(incident.telemetry_snapshot).map(([k, v]) => (
              <div key={k} className="text-xs">
                <span className="text-gray-500">{k.replace(/_/g, ' ')}: </span>
                <span className="text-gray-200">{v}</span>
              </div>
            ))}
          </div>

          {/* AI analysis */}
          {incident.ai_analysis ? (
            <div className="border border-cyan-900 rounded p-3 bg-cyan-950/20">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-cyan-400 uppercase tracking-widest">
                  AI Analysis — LangGraph
                </p>
                <div className="flex items-center gap-2">
                  {incident.llm_cost_usd != null && (
                    <span className="text-xs text-purple-400">${incident.llm_cost_usd}</span>
                  )}
                  {action && (
                    <span className={`text-xs px-2 py-0.5 rounded uppercase tracking-widest ${ACTION_STYLES[action] ?? ACTION_STYLES.monitor}`}>
                      {action}
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs text-gray-300 mb-2">
                {incident.ai_analysis.probable_cause}
              </p>
              <div className="mb-2">
                <p className="text-xs text-gray-500 mb-1">Probable causes</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {incident.ai_analysis.causes.map((c, i) => (
                    <li key={i} className="text-xs text-gray-400">{c}</li>
                  ))}
                </ul>
              </div>
              <div className="mb-2">
                <p className="text-xs text-gray-500 mb-1">Recommended actions</p>
                <ol className="list-decimal list-inside space-y-0.5">
                  {incident.ai_analysis.actions.map((a, i) => (
                    <li key={i} className="text-xs text-gray-300">{a}</li>
                  ))}
                </ol>
              </div>
              {incident.ai_analysis.safety_note && (
                <div className="mt-2 flex gap-1.5 text-xs text-yellow-400">
                  <span>⚠</span>
                  <span>{incident.ai_analysis.safety_note}</span>
                </div>
              )}
              <p className="text-xs text-gray-600 mt-2">
                Urgency: <span className="text-gray-400">{incident.ai_analysis.urgency}</span>
                {incident.ai_analysis.input_tokens > 0 && (
                  <span className="ml-3">
                    Tokens: <span className="text-gray-400">
                      {incident.ai_analysis.input_tokens}↑ {incident.ai_analysis.output_tokens}↓
                    </span>
                  </span>
                )}
              </p>
            </div>
          ) : (
            <p className="text-xs text-gray-600 italic">No AI analysis (key not configured or cooling down)</p>
          )}

          {/* Status badges + actions */}
          <div className="flex items-center gap-2 mt-3">
            {incident.acknowledged && (
              <span className="text-xs text-blue-400 border border-blue-800 px-2 py-0.5 rounded">
                Acknowledged
              </span>
            )}
            {incident.resolved && (
              <span className="text-xs text-green-400 border border-green-800 px-2 py-0.5 rounded">
                Resolved
              </span>
            )}
            {isFP ? (
              <span className="text-xs text-gray-500 border border-gray-700 px-2 py-0.5 rounded">
                False Positive
              </span>
            ) : (
              <button
                onClick={handleFalsePositive}
                className="text-xs text-gray-500 border border-gray-700 px-2 py-0.5 rounded hover:text-red-400 hover:border-red-800 transition-colors"
              >
                Mark as false positive
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function IncidentPanel({ incidents = [] }) {
  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-gray-400 uppercase tracking-widest">
          Incident Log
        </p>
        <span className="text-xs text-gray-600">{incidents.length} total</span>
      </div>

      {incidents.length === 0 ? (
        <div className="text-center py-8 text-gray-600 text-xs">
          No incidents — system operating normally
        </div>
      ) : (
        <div className="max-h-96 overflow-y-auto pr-1">
          {incidents.map((inc) => (
            <IncidentRow key={inc.id} incident={inc} />
          ))}
        </div>
      )}
    </div>
  );
}
