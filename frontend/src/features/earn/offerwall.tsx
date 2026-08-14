import { PageHeader } from '@/components/shared/page-header'
import { OfferFeed } from './offer-feed'

export function OfferwallPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Offerwall"
        description="Provider offers curated for your region and device"
      />
      <OfferFeed emptyTitle="No offerwall tasks available" />
    </div>
  )
}
