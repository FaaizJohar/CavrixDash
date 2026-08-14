import { LogOut, Settings, Shield, User } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useAuth } from '@/stores/auth'
import { initials } from '@/lib/utils'
import { canAccessAdmin } from '@/lib/roles'
import { useNavigate } from 'react-router-dom'

export function UserMenu() {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const navigate = useNavigate()

  if (!user) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 rounded-full p-0.5 transition-opacity hover:opacity-80">
          <Avatar className="h-8 w-8">
            <AvatarImage src={user.avatar_url || undefined} />
            <AvatarFallback>{initials(user.display_name || user.username)}</AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="text-sm font-semibold">{user.display_name || user.username}</div>
          <div className="text-xs font-normal text-muted-foreground">{user.email}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate('/settings')}>
          <User className="h-4 w-4" /> Profile
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => navigate('/settings')}>
          <Settings className="h-4 w-4" /> Settings
        </DropdownMenuItem>
        {user.is_admin && (
          <DropdownMenuItem onClick={() => navigate('/admin')}>
            <Shield className="h-4 w-4" /> Super Admin
          </DropdownMenuItem>
        )}
        {!user.is_admin && canAccessAdmin(user.roles ?? []) && (
          <DropdownMenuItem onClick={() => navigate('/admin')}>
            <Shield className="h-4 w-4" /> Admin Panel
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onClick={async () => {
            await logout()
            navigate('/login')
          }}
        >
          <LogOut className="h-4 w-4" /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
