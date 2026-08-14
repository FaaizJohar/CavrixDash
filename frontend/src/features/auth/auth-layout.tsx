import { Logo } from '@/components/layout/logo'
import { Shield, Coins, Server } from 'lucide-react'

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden border-r border-border bg-card/40 p-10 lg:flex">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(800px 400px at 20% 0%, rgba(59,87,255,0.18), transparent 60%), radial-gradient(600px 400px at 100% 100%, rgba(34,211,238,0.12), transparent 55%)',
          }}
        />
        <div className="relative">
          <Logo />
        </div>
        <div className="relative space-y-8">
          <div>
            <h1 className="text-3xl font-bold leading-tight tracking-tight">
              Earn CVX.
              <br />
              Unlock Minecraft.
              <br />
              <span className="text-gradient">Upgrade your server.</span>
            </h1>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
              Complete legitimate tasks and offers to earn CVX credits, then claim and upgrade free Minecraft
              servers backed by Pterodactyl infrastructure.
            </p>
          </div>
          <div className="flex gap-6">
            {[
              { icon: Coins, label: 'Earn' },
              { icon: Server, label: 'Build' },
              { icon: Shield, label: 'Secure' },
            ].map((f) => (
              <div key={f.label} className="flex flex-col items-center gap-2">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/5">
                  <f.icon className="h-5 w-5 text-cavrix-400" />
                </div>
                <span className="text-xs font-medium text-muted-foreground">{f.label}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="relative text-xs text-muted-foreground">
          © {new Date().getFullYear()} Cavrix Core Technologies
        </div>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-col items-center justify-center px-4 py-10 lg:w-1/2">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex justify-center lg:hidden">
            <Logo />
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
