import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Coins,
  Gift,
  Server,
  BarChart3,
  Users,
  LifeBuoy,
  Settings,
  Command,
  Shield,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useAuth } from '@/stores/auth'
import { canAccessAdmin } from '@/lib/roles'
import { Logo } from './logo'

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  end?: boolean
  adminOnly?: boolean
  children?: { to: string; label: string }[]
}

const mainNav: NavItem[] = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/earn', label: 'Earn', icon: Coins },
  { to: '/rewards', label: 'Rewards', icon: Gift },
  { to: '/minecraft', label: 'Minecraft', icon: Server },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/referrals', label: 'Referrals', icon: Users },
  { to: '/support', label: 'Support', icon: LifeBuoy },
  { to: '/settings', label: 'Settings', icon: Settings },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const user = useAuth((s) => s.user)

  const nav: NavItem[] = canAccessAdmin(user?.roles ?? [])
    ? [...mainNav, { to: '/admin', label: 'Admin Panel', icon: Shield }]
    : mainNav

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-background/95 backdrop-blur-xl transition-transform duration-200 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-border px-5">
          <Logo />
          <button className="lg:hidden" onClick={onClose}>
            <X className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>
        <ScrollArea className="flex-1">
          <nav className="flex flex-col gap-1 p-3">
            {nav.map((item) => (
              <div key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                    )
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </NavLink>
              </div>
            ))}
          </nav>
        </ScrollArea>
        <div className="border-t border-border p-3 text-center text-[11px] text-muted-foreground">
          <div className="flex items-center justify-center gap-1">
            <Command className="h-3 w-3" /> Ctrl + K to search
          </div>
        </div>
      </aside>
    </>
  )
}
