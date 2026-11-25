import { Route, Routes } from 'react-router'

import { Layout } from '@/components/Layout'
import { CampaignCreatePage } from '@/routes/CampaignCreatePage'
import { CampaignEditorPage } from '@/routes/CampaignEditorPage'
import { CampaignListPage } from '@/routes/CampaignListPage'
import { NotFoundPage } from '@/routes/NotFoundPage'

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CampaignListPage />} />
        <Route path="campaigns/new" element={<CampaignCreatePage />} />
        <Route path="campaigns/:id" element={<CampaignEditorPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
