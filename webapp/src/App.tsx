import { useRawInitData } from '@telegram-apps/sdk-react'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/AppShell'
import { ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { ApiProvider, useMe } from '@/lib/queries'
import { EmployeesPage } from '@/pages/EmployeesPage'
import { NewReportPage } from '@/pages/NewReportPage'
import { ReportDetailPage } from '@/pages/ReportDetailPage'
import { ReportsPage } from '@/pages/ReportsPage'

function Shell() {
  const me = useMe()

  if (me.isLoading) return <LoadingScreen />
  if (me.error) return <ErrorScreen error={me.error} />
  if (!me.data) return <ErrorScreen error={new Error('Foydalanuvchi topilmadi')} />

  const isAdmin = me.data.role === 'admin' || me.data.role === 'superadmin'

  return (
    <Routes>
      <Route element={<AppShell me={me.data} />}>
        <Route index element={<ReportsPage />} />
        <Route path="new" element={<NewReportPage />} />
        <Route path="reports/:id" element={<ReportDetailPage />} />
        <Route
          path="employees"
          element={isAdmin ? <EmployeesPage /> : <Navigate to="/" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export function App() {
  // Telegram bergan imzolangan ma'lumot. Brauzerda ochilganda bo'lmaydi —
  // lokal ishlab chiqish uchun VITE_DEV_INIT_DATA dan olinadi. Faqat dev
  // build'da ishlatiladi — aks holda prod build'ga haqiqiy imzolangan
  // initData qattiq yozilib qolishi xavfi bor.
  const rawInitData = useRawInitData()
  const initData = rawInitData || (import.meta.env.DEV ? import.meta.env.VITE_DEV_INIT_DATA : undefined)

  if (!initData) {
    return (
      <ErrorScreen
        error={
          new Error(
            'Bu sahifa Telegram ichida ochilishi kerak. Lokal sinov uchun .env.local ga VITE_DEV_INIT_DATA yozing.',
          )
        }
      />
    )
  }

  return (
    <ApiProvider initData={initData}>
      {/* HashRouter: server tomonida yo'nalish sozlamasi talab qilmaydi va
          Telegram qo'shadigan query parametrlariga xalaqit bermaydi. */}
      <HashRouter>
        <Shell />
      </HashRouter>
    </ApiProvider>
  )
}
