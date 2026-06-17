import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const CustomTooltip = ({ active, payload, label, unit }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-xs">
      <p className="text-gray-400 mb-1">{label}</p>
      <p className="text-white font-bold">
        {payload[0].value?.toFixed(1)} {unit}
      </p>
    </div>
  );
};

/**
 * @param {string}  title
 * @param {Array}   data        — [{time, value}]
 * @param {string}  unit
 * @param {string}  color
 * @param {number|null} warnLine  — horizontal reference line
 * @param {number|null} critLine
 * @param {number[]} domain      — [min, max] for Y axis
 */
export default function LiveChart({
  title,
  data = [],
  unit = '',
  color = '#22d3ee',
  warnLine = null,
  critLine = null,
  domain = ['auto', 'auto'],
}) {
  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <p className="text-xs text-gray-400 uppercase tracking-widest mb-3">{title}</p>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="time"
            tick={{ fill: '#6b7280', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={domain}
            tick={{ fill: '#6b7280', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip unit={unit} />} />
          {warnLine && (
            <ReferenceLine y={warnLine} stroke="#f59e0b" strokeDasharray="4 4" />
          )}
          {critLine && (
            <ReferenceLine y={critLine} stroke="#ef4444" strokeDasharray="4 4" />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: color }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
