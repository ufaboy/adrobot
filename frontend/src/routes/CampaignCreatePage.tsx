import { useNavigate } from 'react-router'

import { CampaignCreateForm } from '@/components/CampaignCreateForm'
import { LoadError } from '@/components/LoadError'
import { useCreateCampaign, useReference } from '@/hooks/use-campaign-creator'
import { useSingleFlight } from '@/hooks/use-single-flight'

export function CampaignCreatePage() {
  const navigate = useNavigate()
  const reference = useReference()
  const create = useCreateCampaign()
  const createOnce = useSingleFlight(create)

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
        <LoadError
          title="Could not load Keitaro data"
          error={reference.error}
          onRetry={() => void reference.refetch()}
          retrying={reference.isFetching}
        />
      )}

      {reference.isSuccess && (
        <CampaignCreateForm
          reference={reference.data}
          isSubmitting={create.isPending}
          submitError={create.error?.message ?? null}
          onSubmit={(data) =>
            createOnce(data, {
              onSuccess: (campaign) =>
                navigate(`/campaigns/${campaign.id}`, { state: { created: campaign } }),
            })
          }
        />
      )}
    </section>
  )
}
