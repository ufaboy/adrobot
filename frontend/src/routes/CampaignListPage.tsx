import { Link } from 'react-router'

export function CampaignListPage() {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Campaigns</h1>
        <Link
          to="/campaigns/new"
          className="rounded-md bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-700"
        >
          New campaign
        </Link>
      </div>
      <p className="text-sm text-slate-500">Campaign list is not implemented yet.</p>
    </section>
  )
}
