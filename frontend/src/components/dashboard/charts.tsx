import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

interface ChartTooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; color?: string }>
  label?: string | number
  formatter?: (value: number) => string
}

function ChartTooltip({ active, payload, label, formatter }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-soft">
      {label !== undefined && <div className="mb-1 font-medium text-muted-foreground">{label}</div>}
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color || '#3b57ff' }} />
          <span className="text-muted-foreground">{p.name}</span>
          <span className="ml-auto font-semibold tabular">
            {formatter ? formatter(p.value) : p.value}
          </span>
        </div>
      ))}
    </div>
  )
}

export function RevenueAreaChart({
  data,
  formatter,
  height = 280,
}: {
  data: Array<Record<string, unknown>>
  formatter?: (v: number) => string
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b57ff" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#3b57ff" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="cvx" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} width={48} />
        <Tooltip content={<ChartTooltip formatter={formatter} />} />
        <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#3b57ff" strokeWidth={2} fill="url(#rev)" />
        <Area type="monotone" dataKey="cvx" name="CVX" stroke="#f59e0b" strokeWidth={2} fill="url(#cvx)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function TrendLineChart({
  data,
  formatter,
  height = 240,
}: {
  data: Array<Record<string, unknown>>
  formatter?: (v: number) => string
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} width={48} />
        <Tooltip content={<ChartTooltip formatter={formatter} />} />
        <Line type="monotone" dataKey="value" name="Value" stroke="#3b57ff" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function RevenueBarChart({
  data,
  formatter,
  height = 240,
}: {
  data: Array<Record<string, unknown>>
  formatter?: (v: number) => string
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} width={48} />
        <Tooltip content={<ChartTooltip formatter={formatter} />} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="revenue" name="Revenue" fill="#3b57ff" radius={[4, 4, 0, 0]} />
        <Bar dataKey="cost" name="Cost" fill="#64748b" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export { ChartTooltip }
