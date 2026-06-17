export default function Header({ connected, timestamp, anomalyCount }) {
  const ts = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '--:--:--';

  return (
    <div className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-gray-950">
      <div className="flex items-center gap-3">
        <span className="text-yellow-400 text-lg">⚡</span>
        <div>
          <h1 className="text-sm font-bold text-white tracking-widest uppercase">
            Solar Farm — AI Operations Copilot
          </h1>
          <p className="text-xs text-gray-500">FARM-A · Real-time telemetry ingestion system</p>
        </div>
      </div>

      <div className="flex items-center gap-6 text-xs">
        {anomalyCount > 0 && (
          <span className="flex items-center gap-1.5 text-red-400 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
            {anomalyCount} active anomal{anomalyCount === 1 ? 'y' : 'ies'}
          </span>
        )}
        <span className="text-gray-500">
          Last update: <span className="text-gray-300">{ts}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-500 animate-pulse'}`}
          />
          <span className={connected ? 'text-green-400' : 'text-red-400'}>
            {connected ? 'LIVE' : 'RECONNECTING'}
          </span>
        </span>
      </div>
    </div>
  );
}
