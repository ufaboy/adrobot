import { PlusIcon, RefreshCwIcon } from 'lucide-react'
import { Link } from 'react-router'

import { LoadError } from '@/components/LoadError'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCampaigns } from '@/hooks/use-campaign-editor'
import { cn } from '@/lib/utils'

// Mobile first: a campaign is a two-line card (name, then id · alias); from sm up the
// rows line up as a table with ID / Name / Alias / State columns.
const ROW_GRID =
  'grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 sm:grid-cols-[4rem_minmax(0,1fr)_8rem_5rem]'

export function CampaignListPage() {
  const campaigns = useCampaigns()

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Campaigns</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={campaigns.isFetching}
            onClick={() => void campaigns.refetch()}
            title="Reload the list from Keitaro"
            aria-label="Reload the list from Keitaro"
          >
            <RefreshCwIcon className={campaigns.isFetching ? 'animate-spin' : ''} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
          <Button render={<Link to="/campaigns/new" />} nativeButton={false}>
            <PlusIcon />
            New campaign
          </Button>
        </div>
      </div>

      {campaigns.isPending && <p className="text-sm text-muted-foreground">Loading…</p>}

      {campaigns.isError && (
        <LoadError
          title="Could not load campaigns from Keitaro"
          error={campaigns.error}
          onRetry={() => void campaigns.refetch()}
          retrying={campaigns.isFetching}
        />
      )}

      {campaigns.data?.length === 0 && (
        <p className="text-sm text-muted-foreground">No campaigns yet.</p>
      )}

      {campaigns.data && campaigns.data.length > 0 && (
        <div role="table" aria-label="Campaigns" className="rounded-xl border bg-card text-sm">
          <div role="rowgroup" className="hidden sm:block">
            <div
              role="row"
              className={cn(ROW_GRID, 'border-b px-4 py-2 font-medium text-muted-foreground')}
            >
              <span role="columnheader">ID</span>
              <span role="columnheader">Name</span>
              <span role="columnheader">Alias</span>
              <span role="columnheader">State</span>
            </div>
          </div>
          <div role="rowgroup" className="divide-y">
            {campaigns.data.map((campaign) => (
              <div
                role="row"
                key={campaign.id}
                className={cn(ROW_GRID, 'relative px-4 py-3 hover:bg-muted/50 sm:py-2')}
              >
                <span role="cell" className="hidden font-mono text-xs sm:block">
                  {campaign.id}
                </span>
                <span role="cell" className="min-w-0">
                  {/* The link covers the whole row, so the card is one big tap target. */}
                  <Link
                    to={`/campaigns/${campaign.id}`}
                    className="block truncate font-medium after:absolute after:inset-0 hover:underline"
                  >
                    {campaign.name}
                  </Link>
                  <span className="block font-mono text-xs text-muted-foreground sm:hidden">
                    #{campaign.id} · {campaign.alias}
                  </span>
                </span>
                <span role="cell" className="hidden font-mono text-xs sm:block">
                  {campaign.alias}
                </span>
                <span role="cell" className="row-start-1 col-start-2 sm:col-start-auto sm:row-start-auto">
                  <Badge variant="secondary">{campaign.state}</Badge>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
