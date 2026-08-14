import { Bell, Coins, Menu, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/stores/auth'
import { formatNumber } from '@/lib/utils'
import { UserMenu } from './user-menu'
import { NotificationCenter } from '@/components/shared/notification-center'

interface TopbarProps {
  onOpenSidebar: () => void
  onOpenPalette: () => void
}

export function Topbar({ onOpenSidebar, onOpenPalette }: TopbarProps) {
  const user = useAuth((s) => s.user)

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-xl sm:px-6">
      <button className="lg:hidden" onClick={onOpenSidebar}>
        <Menu className="h-5 w-5" />
      </button>

      <button
        onClick={onOpenPalette}
        className="hidden items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent md:flex md:w-72"
      >
        <Search className="h-4 w-4" />
        <span>Search…</span>
        <kbd className="ml-auto rounded border border-border bg-muted px-1.5 py-0.5 text-[10px]">Ctrl K</kbd>
      </button>

      <div className="ml-auto flex items-center gap-2">
        {user && (
          <div className="mr-1 hidden items-center gap-1.5 rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs font-semibold text-amber-300 sm:flex">
            <Coins className="h-3.5 w-3.5" />
            {formatNumber(user.cvx_balance)}
            <span className="text-amber-400/60">CVX</span>
          </div>
        )}
        <NotificationCenter />
        <UserMenu />
      </div>
    </header>
  )
}
