import { useState } from 'react'
import { NavLink, Outlet, Link } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  Coins,
  Server,
  Wallet,
  ShieldAlert,
  BarChart3,
  LifeBuoy,
  Bell,
  FileText,
  Settings,
  KeyRound,
  ArrowLeft,
  Shield,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Logo } from '@/components/layout/logo'
import { useAuth } from '@/stores/auth'
import { adminScopes, adminTitle, type AdminScope } from '@/lib/roles'

interface AdminItem {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  scopes: AdminScope[]
}

interface AdminSection {
  title: string
  items: AdminItem[]
}

const sections: AdminSection[] = [
  {
    title: 'General',
    items: [
      { to: '/admin', label: 'Overview', icon: LayoutDashboard, scopes: ['super', 'admin', 'finance', 'infra'] },
    ],
  },
  {
    title: 'Users',
    items: [{ to: '/admin/users', label: 'All Users', icon: Users, scopes: ['super', 'admin'] }],
  },
  {
    title: 'Earning System',
    items: [
      { to: '/admin/offers', label: 'Offers & Tasks', icon: Coins, scopes: ['super', 'admin', 'finance'] },
      { to: '/admin/providers', label: 'Providers', icon: Shield, scopes: ['super', 'admin', 'finance'] },
      { to: '/admin/conversions', label: 'Conversions', icon: BarChart3, scopes: ['super', 'admin', 'finance'] },
    ],
  },
  {
    title: 'CVX Economy',
    items: [{ to: '/admin/economy', label: 'Economy & Pricing', icon: Wallet, scopes: ['super', 'admin', 'finance'] }],
  },
  {
    title: 'Minecraft',
    items: [{ to: '/admin/minecraft', label: 'Plans & Nodes', icon: Server, scopes: ['super', 'admin', 'infra'] }],
  },
  {
    title: 'Revenue',
    items: [{ to: '/admin/revenue', label: 'Revenue & Profit', icon: BarChart3, scopes: ['super', 'admin', 'finance'] }],
  },
  {
    title: 'Security',
    items: [
      { to: '/admin/fraud', label: 'Fraud & Risk', icon: ShieldAlert, scopes: ['super', 'admin'] },
      { to: '/admin/audit', label: 'Audit Log', icon: FileText, scopes: ['super'] },
    ],
  },
  {
    title: 'Platform',
    items: [
      { to: '/admin/analytics', label: 'Analytics', icon: BarChart3, scopes: ['super', 'admin', 'finance'] },
      { to: '/admin/support', label: 'Support Queue', icon: LifeBuoy, scopes: ['super', 'admin'] },
      { to: '/admin/announcements', label: 'Announcements', icon: Bell, scopes: ['super', 'admin'] },
      { to: '/admin/settings', label: 'Global Settings', icon: Settings, scopes: ['super', 'admin', 'finance'] },
      { to: '/admin/secrets', label: 'Secrets & Tokens', icon: KeyRound, scopes: ['super'] },
    ],
  },
]

export function AdminLayout() {
  const [open, setOpen] = useState(false)
  const user = useAuth((s) => s.user)
  const scopes = adminScopes(user?.roles ?? [])
  const visible = sections
    .map((section) => ({ ...section, items: section.items.filter((i) => i.scopes.some((s) => scopes.includes(s))) }))
    .filter((section) => section.items.length > 0)

  return (
    <div className="min-h-screen">
      {open && <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden" onClick={() => setOpen(false)} />}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-border bg-card/80 backdrop-blur-xl transition-transform duration-200 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-red-500 to-orange-500">
              <Shield className="h-4 w-4 text-white" />
            </div>
            <div>
              <div className="text-xs font-bold tracking-tight">{adminTitle(user?.roles ?? [])}</div>
              <div className="text-[10px] text-muted-foreground">Cavrix Cloud</div>
            </div>
          </div>
          <button className="lg:hidden" onClick={() => setOpen(false)}>
            <X className="h-4 w-4" />
          </button>
        </div>
        <ScrollArea className="flex-1">
          <nav className="p-3">
            {visible.map((section) => (
              <div key={section.title} className="mb-4">
                <div className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  {section.title}
                </div>
                <div className="space-y-0.5">
                  {section.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === '/admin'}
                      onClick={() => setOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-2.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors',
                          isActive
                            ? 'bg-primary/15 text-primary'
                            : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                        )
                      }
                    >
                      <item.icon className="h-3.5 w-3.5 shrink-0" />
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
          </nav>
        </ScrollArea>
        <div className="border-t border-border p-3">
          <NavLink
            to="/"
            className="flex items-center gap-2 rounded-md px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to user dashboard
          </NavLink>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col lg:pl-60">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-xl sm:px-6">
          <button className="lg:hidden" onClick={() => setOpen(true)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12h18M3 6h18M3 18h18" strokeLinecap="round" />
            </svg>
          </button>
          <Logo compact />
          <div className="ml-auto hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
            <span className="status-dot bg-emerald-400" /> Platform online
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
