export const categoryLabels: Record<string, string> = {
  all: 'All',
  apps: 'Apps',
  games: 'Games',
  software: 'Software',
  surveys: 'Surveys',
  trials: 'Trials',
  cpa: 'CPA',
  cpi: 'CPI',
  cpe: 'CPE',
  lead: 'Lead Generation',
  other: 'Other',
}

export const categoryColors: Record<string, string> = {
  apps: 'text-sky-400 bg-sky-400/10 border-sky-400/20',
  games: 'text-violet-400 bg-violet-400/10 border-violet-400/20',
  software: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  surveys: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  trials: 'text-rose-400 bg-rose-400/10 border-rose-400/20',
  cpa: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
  cpi: 'text-fuchsia-400 bg-fuchsia-400/10 border-fuchsia-400/20',
  cpe: 'text-teal-400 bg-teal-400/10 border-teal-400/20',
  lead: 'text-indigo-400 bg-indigo-400/10 border-indigo-400/20',
  other: 'text-slate-400 bg-slate-400/10 border-slate-400/20',
}

export const statusConfig: Record<string, { label: string; dot: string; className: string }> = {
  active: { label: 'Active', dot: 'bg-emerald-400', className: 'text-emerald-400 border-emerald-400/25 bg-emerald-400/10' },
  online: { label: 'Online', dot: 'bg-emerald-400', className: 'text-emerald-400 border-emerald-400/25 bg-emerald-400/10' },
  running: { label: 'Running', dot: 'bg-emerald-400', className: 'text-emerald-400 border-emerald-400/25 bg-emerald-400/10' },
  pending: { label: 'Pending', dot: 'bg-amber-400', className: 'text-amber-400 border-amber-400/25 bg-amber-400/10' },
  held: { label: 'Held', dot: 'bg-amber-400', className: 'text-amber-400 border-amber-400/25 bg-amber-400/10' },
  provisioning: { label: 'Provisioning', dot: 'bg-amber-400', className: 'text-amber-400 border-amber-400/25 bg-amber-400/10' },
  offline: { label: 'Offline', dot: 'bg-slate-400', className: 'text-slate-400 border-slate-400/25 bg-slate-400/10' },
  stopped: { label: 'Stopped', dot: 'bg-slate-400', className: 'text-slate-400 border-slate-400/25 bg-slate-400/10' },
  suspended: { label: 'Suspended', dot: 'bg-orange-400', className: 'text-orange-400 border-orange-400/25 bg-orange-400/10' },
  paused: { label: 'Paused', dot: 'bg-orange-400', className: 'text-orange-400 border-orange-400/25 bg-orange-400/10' },
  banned: { label: 'Banned', dot: 'bg-red-500', className: 'text-red-400 border-red-400/25 bg-red-400/10' },
  rejected: { label: 'Rejected', dot: 'bg-red-500', className: 'text-red-400 border-red-400/25 bg-red-400/10' },
  reversed: { label: 'Reversed', dot: 'bg-red-500', className: 'text-red-400 border-red-400/25 bg-red-400/10' },
  expired: { label: 'Expired', dot: 'bg-slate-500', className: 'text-slate-400 border-slate-400/25 bg-slate-400/10' },
  approved: { label: 'Approved', dot: 'bg-emerald-400', className: 'text-emerald-400 border-emerald-400/25 bg-emerald-400/10' },
  deleted: { label: 'Deleted', dot: 'bg-slate-500', className: 'text-slate-400 border-slate-400/25 bg-slate-400/10' },
  disabled: { label: 'Disabled', dot: 'bg-slate-500', className: 'text-slate-400 border-slate-400/25 bg-slate-400/10' },
  error: { label: 'Error', dot: 'bg-red-500', className: 'text-red-400 border-red-400/25 bg-red-400/10' },
  connected: { label: 'Connected', dot: 'bg-emerald-400', className: 'text-emerald-400 border-emerald-400/25 bg-emerald-400/10' },
  disconnected: { label: 'Disconnected', dot: 'bg-slate-500', className: 'text-slate-400 border-slate-400/25 bg-slate-400/10' },
  hidden: { label: 'Hidden', dot: 'bg-slate-500', className: 'text-slate-400 border-slate-400/25 bg-slate-400/10' },
}

export function statusOf(value: string | undefined) {
  return statusConfig[value || ''] || {
    label: value || '—',
    dot: 'bg-slate-500',
    className: 'text-slate-400 border-slate-400/25 bg-slate-400/10',
  }
}

export const ledgerTypeLabels: Record<string, string> = {
  CREDIT: 'Earned',
  DEBIT: 'Spent',
  REVERSAL: 'Reversal',
  BONUS: 'Bonus',
  ADJUSTMENT: 'Adjustment',
  REFUND: 'Refund',
  SERVER_PURCHASE: 'Server Claim',
  UPGRADE: 'Upgrade',
}

export const ledgerTypeColors: Record<string, string> = {
  CREDIT: 'text-emerald-400',
  DEBIT: 'text-slate-300',
  REVERSAL: 'text-red-400',
  BONUS: 'text-amber-400',
  ADJUSTMENT: 'text-sky-400',
  REFUND: 'text-teal-400',
  SERVER_PURCHASE: 'text-violet-400',
  UPGRADE: 'text-cyan-400',
}

export function deviceLabels(devices: string[]): string {
  if (!devices?.length) return 'Any device'
  const map: Record<string, string> = { android: 'Android', ios: 'iOS', web: 'Web' }
  return devices.map((d) => map[d] || d).join(' · ')
}

export function sortOptions() {
  return [
    { value: 'recommended', label: 'Recommended' },
    { value: 'reward', label: 'Highest reward' },
    { value: 'new', label: 'Newest' },
    { value: 'fastest', label: 'Fastest' },
    { value: 'conversion', label: 'Highest conversion' },
    { value: 'reliable', label: 'Most reliable' },
  ]
}
