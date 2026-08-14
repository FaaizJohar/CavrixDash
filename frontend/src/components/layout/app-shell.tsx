import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './sidebar'
import { Topbar } from './topbar'
import { BottomNav } from './bottom-nav'
import { CommandPalette } from '@/components/shared/command-palette'
import { useHotkeys } from '@/hooks/use-hotkeys'

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)

  useHotkeys(['ctrl+k', 'meta+k'], (e) => {
    e.preventDefault()
    setPaletteOpen((v) => !v)
  })

  return (
    <div className="min-h-screen">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-h-screen flex-col lg:pl-64">
        <Topbar onOpenSidebar={() => setSidebarOpen(true)} onOpenPalette={() => setPaletteOpen(true)} />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 pb-24 sm:px-6 lg:pb-8">
          <Outlet />
        </main>
      </div>
      <BottomNav />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  )
}
