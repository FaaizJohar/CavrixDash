import { Clock, Flame, Star, Zap } from 'lucide-react'
import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import { CvxBadge } from '@/components/shared/cvx-badge'
import { categoryColors, categoryLabels, deviceLabels } from '@/lib/labels'
import { cn } from '@/lib/utils'
import type { OfferOut } from '@/types'

interface OfferCardProps {
  offer: OfferOut
  onStart?: (offer: OfferOut) => void
  loading?: boolean
  compact?: boolean
}

export function OfferCard({ offer, onStart, loading, compact }: OfferCardProps) {
  const catColor = categoryColors[offer.category] || categoryColors.other

  return (
    <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }}>
      <Card className="flex h-full flex-col overflow-hidden">
        <CardHeader className="flex-row items-start justify-between space-y-0 gap-3 p-4 pb-0">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border bg-muted">
              {offer.icon_url ? (
                <img src={offer.icon_url} alt="" className="h-full w-full object-cover" />
              ) : (
                <span className="text-lg font-bold text-muted-foreground">{offer.title.charAt(0)}</span>
              )}
            </div>
            <div className="min-w-0">
              <div className="line-clamp-1 text-sm font-semibold">{offer.title}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">{offer.provider_name}</div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {offer.featured && (
              <Badge variant="warning" className="gap-1">
                <Star className="h-3 w-3" /> Featured
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex-1 p-4">
          {offer.description && (
            <p className="line-clamp-2 text-xs text-muted-foreground">{offer.description}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-1.5">
            <Badge variant="outline" className={cn('border', catColor)}>
              {categoryLabels[offer.category] || offer.category}
            </Badge>
            {offer.devices?.map((d) => (
              <Badge key={d} variant="muted" className="capitalize">
                {d}
              </Badge>
            ))}
          </div>
          <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
            {offer.estimated_time > 0 && (
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" /> ~{offer.estimated_time} min
              </span>
            )}
            {offer.conversion_rate > 0 && (
              <span className="flex items-center gap-1">
                <Flame className="h-3.5 w-3.5 text-orange-400" /> {Math.round(offer.conversion_rate * 100)}% convert
              </span>
            )}
            {offer.approval_rate > 0 && (
              <span className="flex items-center gap-1">
                <Zap className="h-3.5 w-3.5 text-yellow-400" /> {Math.round(offer.approval_rate * 100)}% approve
              </span>
            )}
          </div>
        </CardContent>
        <CardFooter className="items-center justify-between p-4 pt-0">
          <CvxBadge value={offer.effective_reward} />
          <Button
            size="sm"
            loading={loading}
            disabled={offer.status !== 'active'}
            onClick={() => onStart?.(offer)}
          >
            {offer.status === 'active' ? 'Start' : 'Unavailable'}
          </Button>
        </CardFooter>
      </Card>
    </motion.div>
  )
}
