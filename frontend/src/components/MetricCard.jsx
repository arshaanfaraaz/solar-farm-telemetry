const SEVERITY_RING = {
  CRITICAL: 'ring-1 ring-red-500 bg-red-950/20',
  HIGH:     'ring-1 ring-orange-500 bg-orange-950/20',
  MEDIUM:   'ring-1 ring-yellow-500 bg-yellow-950/10',
  LOW:      'ring-1 ring-yellow-700 bg-yellow-950/10',
};

/**
 * @param {string}  label
 * @param {number|string} value
 * @param {string}  unit
 * @param {string}  icon      — emoji or symbol
 * @param {string|null} anomalySeverity — null means healthy
 * @param {string|null} anomalyMsg
 * @param {string}  subtext   — e.g. "nominal 395–405 V"
 */
export default function MetricCard({
  label,
  value,
  unit,
  icon,
  anomalySeverity = null,
  anomalyMsg = null,
  subtext = '',
}) {
  const ring = anomalySeverity ? SEVERITY_RING[anomalySeverity] ?? '' : '';

  const valueColor = anomalySeverity
    ? anomalySeverity === 'CRITICAL' ? 'text-red-400'
    : anomalySeverity === 'HIGH'     ? 'text-orange-400'
    : 'text-yellow-400'
    : 'text-green-400';

  return (
    <div className={`rounded-lg p-4 bg-gray-900 transition-all duration-300 ${ring}`}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-gray-400 text-xs uppercase tracking-widest">{label}</span>
        <span className="text-lg">{icon}</span>
      </div>

      <div className="flex items-end gap-1.5 mb-1">
        <span className={`text-2xl font-bold tabular-nums ${valueColor}`}>
          {value ?? '—'}
        </span>
        <span className="text-gray-500 text-sm mb-0.5">{unit}</span>
      </div>

      {anomalyMsg ? (
        <p className={`text-xs mt-1 ${valueColor}`}>{anomalyMsg}</p>
      ) : (
        <p className="text-xs text-gray-600 mt-1">{subtext}</p>
      )}
    </div>
  );
}
