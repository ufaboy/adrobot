import { Link, Outlet } from 'react-router'

import { useHealth } from '@/hooks/use-health'

export function Layout() {
  const health = useHealth()

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="font-semibold">
            Adrobot · Keitaro wrapper
          </Link>
          <span className="text-xs text-slate-500" data-testid="api-status">
            API: {health.isSuccess ? 'online' : health.isError ? 'offline' : '…'}
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
