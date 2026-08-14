import { Logo } from '@/components/layout/logo'

export function Splash() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <Logo />
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary"
            style={{ animationDelay: `${i * 0.12}s` }}
          />
        ))}
      </div>
    </div>
  )
}
