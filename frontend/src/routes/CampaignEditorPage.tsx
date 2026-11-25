import { useParams } from 'react-router'

export function CampaignEditorPage() {
  const { id } = useParams()

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Campaign #{id}</h1>
      <p className="text-sm text-slate-500">Campaign editor is not implemented yet.</p>
    </section>
  )
}
