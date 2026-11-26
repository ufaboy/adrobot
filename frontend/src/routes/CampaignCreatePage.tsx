import { useNavigate } from 'react-router'

import { CampaignCreateForm } from '@/components/CampaignCreateForm'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useCreateCampaign, useReference } from '@/hooks/use-campaign-creator'

export function CampaignCreatePage() {
  const navigate = useNavigate()
  const reference = useReference()
  const create = useCreateCampaign()

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">New campaign</h1>
        <p className="text-sm text-muted-foreground">
          Creates a Keitaro campaign with a geo-redirect stream and an offer stream.
        </p>
      </div>

      {reference.isPending && <p className="text-sm text-muted-foreground">Loading…</p>}

      {reference.isError && (
        <Alert variant="destructive">
          <AlertTitle>Could not load Keitaro data</AlertTitle>
          <AlertDescription>{reference.error.message}</AlertDescription>
        </Alert>
      )}

      {reference.isSuccess && (
        <CampaignCreateForm
          reference={reference.data}
          isSubmitting={create.isPending}
          submitError={create.error?.message ?? null}
          onSubmit={(data) =>
            create.mutate(data, {
              onSuccess: (campaign) =>
                navigate(`/campaigns/${campaign.id}`, { state: { created: campaign } }),
            })
          }
        />
      )}
    </section>
  )
}
