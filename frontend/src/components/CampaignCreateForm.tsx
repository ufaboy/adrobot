import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

import { CountryMultiSelect } from '@/components/CountryMultiSelect'
import { IdSelect } from '@/components/IdSelect'
import { OfferCombobox } from '@/components/OfferCombobox'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import type { CampaignCreateRequest, Offer, ReferenceData } from '@/lib/api'

const idField = (message: string) => z.number({ error: message }).int().positive()

const campaignFormSchema = z.object({
  name: z.string().trim().min(1, 'Name is required').max(255, 'Name is too long'),
  geo: z.array(z.string()).min(1, 'Select at least one country'),
  offerId: idField('Select an offer'),
  domainId: idField('Select a domain'),
  groupId: idField('Select a group'),
  trafficSourceId: idField('Select a traffic source'),
})

type FormInput = z.input<typeof campaignFormSchema>
type FormOutput = z.output<typeof campaignFormSchema>

interface CampaignCreateFormProps {
  reference: ReferenceData
  onSubmit: (data: CampaignCreateRequest) => void
  isSubmitting: boolean
  submitError: string | null
}

export function CampaignCreateForm({
  reference,
  onSubmit,
  isSubmitting,
  submitError,
}: CampaignCreateFormProps) {
  const [offer, setOffer] = useState<Offer | null>(null)
  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(campaignFormSchema),
    defaultValues: {
      name: '',
      geo: [],
      domainId: reference.defaults.domain_id ?? undefined,
      groupId: reference.defaults.group_id ?? undefined,
      trafficSourceId: reference.defaults.traffic_source_id ?? undefined,
    },
  })

  const submit = form.handleSubmit((values) =>
    onSubmit({
      name: values.name,
      geo: values.geo,
      offer_id: values.offerId,
      domain_id: values.domainId,
      group_id: values.groupId,
      traffic_source_id: values.trafficSourceId,
    }),
  )

  return (
    <form onSubmit={submit} noValidate className="max-w-xl">
      <FieldGroup>
        <Controller
          name="name"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="campaign-name">Name</FieldLabel>
              <Input
                {...field}
                id="campaign-name"
                placeholder="Campaign name"
                autoComplete="off"
                aria-invalid={fieldState.invalid}
              />
              <FieldError errors={[fieldState.error]} />
            </Field>
          )}
        />

        <Controller
          name="geo"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="campaign-geo">Geo</FieldLabel>
              <CountryMultiSelect
                id="campaign-geo"
                countries={reference.countries}
                value={field.value}
                onChange={field.onChange}
                invalid={fieldState.invalid}
              />
              <FieldDescription>
                Visitors from these countries are redirected to Google; everyone else goes to the
                offer.
              </FieldDescription>
              <FieldError errors={[fieldState.error]} />
            </Field>
          )}
        />

        <Controller
          name="offerId"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="campaign-offer">Offer</FieldLabel>
              <OfferCombobox
                id="campaign-offer"
                value={offer}
                onChange={(next) => {
                  setOffer(next)
                  field.onChange(next?.id)
                }}
                invalid={fieldState.invalid}
              />
              <FieldError errors={[fieldState.error]} />
            </Field>
          )}
        />

        <div className="grid gap-4 sm:grid-cols-3">
          {(
            [
              ['domainId', 'Domain', reference.domains],
              ['groupId', 'Group', reference.groups],
              ['trafficSourceId', 'Traffic source', reference.traffic_sources],
            ] as const
          ).map(([name, label, items]) => (
            <Controller
              key={name}
              name={name}
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={`campaign-${name}`}>{label}</FieldLabel>
                  <IdSelect
                    id={`campaign-${name}`}
                    items={items}
                    value={field.value}
                    onChange={field.onChange}
                    placeholder={`Select ${label.toLowerCase()}`}
                    invalid={fieldState.invalid}
                  />
                  <FieldError errors={[fieldState.error]} />
                </Field>
              )}
            />
          ))}
        </div>

        {submitError && (
          <Alert variant="destructive">
            <AlertTitle>Campaign was not created</AlertTitle>
            <AlertDescription>{submitError}</AlertDescription>
          </Alert>
        )}

        <div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating…' : 'Create campaign'}
          </Button>
        </div>
      </FieldGroup>
    </form>
  )
}
