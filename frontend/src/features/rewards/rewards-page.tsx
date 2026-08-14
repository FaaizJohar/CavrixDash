import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { PageHeader } from '@/components/shared/page-header'
import { Wallet, Server, ArrowUpCircle } from 'lucide-react'
import { WalletPage } from './wallet'
import { ServersRewardPage } from './servers'
import { UpgradesPage } from './upgrades'

export function RewardsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Rewards"
        description="Spend your CVX on free servers, upgrades, and more"
      />
      <Tabs defaultValue="wallet">
        <TabsList>
          <TabsTrigger value="wallet">
            <Wallet className="mr-1.5 h-3.5 w-3.5" /> CVX Wallet
          </TabsTrigger>
          <TabsTrigger value="servers">
            <Server className="mr-1.5 h-3.5 w-3.5" /> Free Servers
          </TabsTrigger>
          <TabsTrigger value="upgrades">
            <ArrowUpCircle className="mr-1.5 h-3.5 w-3.5" /> Upgrades
          </TabsTrigger>
        </TabsList>
        <TabsContent value="wallet" className="mt-4">
          <WalletPage />
        </TabsContent>
        <TabsContent value="servers" className="mt-4">
          <ServersRewardPage />
        </TabsContent>
        <TabsContent value="upgrades" className="mt-4">
          <UpgradesPage />
        </TabsContent>
      </Tabs>
    </div>
  )
}
