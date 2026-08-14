import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface PaginationProps {
  page: number
  pages: number
  total: number
  pageSize: number
  onChange: (page: number) => void
  className?: string
}

export function Pagination({ page, pages, total, pageSize, onChange, className }: PaginationProps) {
  if (pages <= 1) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)

  const pagesToShow = new Set<number>([1, pages, page, page - 1, page + 1])
  const sorted = Array.from(pagesToShow)
    .filter((p) => p >= 1 && p <= pages)
    .sort((a, b) => a - b)

  const items: React.ReactNode[] = []
  let prev = 0
  for (const p of sorted) {
    if (p - prev > 1) {
      items.push(
        <span key={`gap-${p}`} className="px-1 text-muted-foreground">
          …
        </span>,
      )
    }
    items.push(
      <Button
        key={p}
        variant={p === page ? 'default' : 'ghost'}
        size="iconSm"
        className={cn('text-xs', p === page && '')}
        onClick={() => onChange(p)}
      >
        {p}
      </Button>,
    )
    prev = p
  }

  return (
    <div className={cn('flex flex-col items-center justify-between gap-3 sm:flex-row', className)}>
      <div className="text-xs text-muted-foreground">
        Showing {from}–{to} of {total}
      </div>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="iconSm"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        {items}
        <Button
          variant="outline"
          size="iconSm"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
