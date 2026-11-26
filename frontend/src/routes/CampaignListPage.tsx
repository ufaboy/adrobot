import { PlusIcon } from 'lucide-react'
import { Link } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useCampaigns } from '@/hooks/use-campaign-editor'

export function CampaignListPage() {
  const campaigns = useCampaigns()

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Campaigns</h1>
        <Button render={<Link to="/campaigns/new" />} nativeButton={false}>
          <PlusIcon />
          New campaign
        </Button>
      </div>

      {campaigns.isPending && <p className="text-sm text-muted-foreground">Loading…</p>}

      {campaigns.isError && (
        <Alert variant="destructive">
          <AlertTitle>Could not load campaigns from Keitaro</AlertTitle>
          <AlertDescription>{campaigns.error.message}</AlertDescription>
        </Alert>
      )}

      {campaigns.data?.length === 0 && (
        <p className="text-sm text-muted-foreground">No campaigns yet.</p>
      )}

      {campaigns.data && campaigns.data.length > 0 && (
        <div className="rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead className="w-32">Alias</TableHead>
                <TableHead className="w-24">State</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaigns.data.map((campaign) => (
                <TableRow key={campaign.id}>
                  <TableCell className="font-mono text-xs">{campaign.id}</TableCell>
                  <TableCell>
                    <Link
                      to={`/campaigns/${campaign.id}`}
                      className="font-medium hover:underline"
                    >
                      {campaign.name}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{campaign.alias}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{campaign.state}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  )
}
