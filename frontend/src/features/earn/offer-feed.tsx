import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, showError } from '@/lib/api'
import type { OfferOut, ClickResponse, Paginated } from '@/types'
import { OfferCard } from '@/components/dashboard/offer-card'
import { SkeletonGrid } from '@/components/shared/skeleton'
import { EmptyState } from '@/components/shared/empty-state'
import { ErrorState } from '@/components/shared/error-state'
import { Pagination } from '@/components/shared/pagination'
import { Inbox } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { sortOptions } from '@/lib/labels'
import { Button } from '@/components/ui/button'
import { useMutation } from '@tanstack/react-query'

interface OfferFeedProps {
  category?: string
  devices?: string[]
  countries?: string[]
  emptyTitle?: string
  emptyDescription?: string
}

export function OfferFeed({
  category,
  devices,
  countries,
  emptyTitle = 'No tasks available',
  emptyDescription = 'New offers are added regularly. Check back soon.',
}: OfferFeedProps) {
  const [sort, setSort] = useState('recommended')
  const [device, setDevice] = useState('')
  const [page, setPage] = useState(1)
  const [starting, setStarting] = useState<string | null>(null)

  const params = new URLSearchParams({
    page: String(page),
    page_size: '24',
    sort,
  })
  if (category && category !== 'all') params.set('category', category)
  if (device) params.set('device', device)
  if (countries?.length) params.set('country', countries[0])

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['offers', { category, sort, device, countries, page }],
    queryFn: () => api.get<Paginated<OfferOut>>(`/offers?${params.toString()}`),
    placeholderData: (prev) => prev,
  })

  const startMutation = useMutation({
    mutationFn: async (offer: OfferOut) => {
      setStarting(offer.id)
      try {
        const res = await api.post<ClickResponse>(`/offers/${offer.id}/click`)
        return res
      } finally {
        setStarting(null)
      }
    },
    onSuccess: (res) => {
      window.open(res.redirect_url, '_blank', 'noopener')
      toast.success('Offer started — complete it to earn CVX')
    },
    onError: (err) => showError(err),
  })

  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={sort} onValueChange={(v) => { setSort(v); setPage(1) }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Sort" />
          </SelectTrigger>
          <SelectContent>
            {sortOptions().map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={device} onValueChange={(v) => { setDevice(v); setPage(1) }}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="All devices" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All devices</SelectItem>
            <SelectItem value="android">Android</SelectItem>
            <SelectItem value="ios">iOS</SelectItem>
            <SelectItem value="web">Web</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <SkeletonGrid count={6} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState icon={Inbox} title={emptyTitle} description={emptyDescription} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((offer) => (
              <OfferCard
                key={offer.id}
                offer={offer}
                loading={starting === offer.id}
                onStart={(o) => startMutation.mutate(o)}
              />
            ))}
          </div>
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            pageSize={data.page_size}
            onChange={setPage}
          />
        </>
      )}
    </div>
  )
}
