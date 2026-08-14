import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { PageHeader } from '@/components/shared/page-header'
import { Coins, ListChecks, LayoutGrid } from 'lucide-react'
import { OfferFeed } from './offer-feed'
import { MyTasks } from './my-tasks'

export function EarnPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Earn CVX"
        description="Complete tasks and offers to earn credits for your Minecraft servers"
        actions={
          <div className="flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs font-semibold text-amber-300">
            <Coins className="h-3.5 w-3.5" /> Verified actions only
          </div>
        }
      />

      <Tabs defaultValue="tasks">
        <TabsList>
          <TabsTrigger value="tasks">
            <LayoutGrid className="mr-1.5 h-3.5 w-3.5" /> Tasks
          </TabsTrigger>
          <TabsTrigger value="my-tasks">
            <ListChecks className="mr-1.5 h-3.5 w-3.5" /> My Tasks
          </TabsTrigger>
        </TabsList>
        <TabsContent value="tasks" className="mt-4">
          <OfferFeed />
        </TabsContent>
        <TabsContent value="my-tasks" className="mt-4">
          <MyTasks />
        </TabsContent>
      </Tabs>
    </div>
  )
}
