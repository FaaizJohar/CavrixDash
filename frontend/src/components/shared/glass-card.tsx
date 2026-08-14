import { cn } from '@/lib/utils'

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  interactive?: boolean
}

export function GlassCard({ className, interactive, ...props }: GlassCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl glass-soft',
        interactive &&
          'transition-all duration-200 hover:border-white/15 hover:bg-card/60 cursor-pointer',
        className,
      )}
      {...props}
    />
  )
}
