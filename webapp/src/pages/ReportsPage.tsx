import { ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyScreen, ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { Report, ReportStatus } from '@/lib/api'
import { useMe, useReports } from '@/lib/queries'
import { formatTime, toApiDate } from '@/lib/utils'

const FILTERS: { key: ReportStatus | 'all'; label: string }[] = [
  { key: 'pending', label: 'Kutilmoqda' },
  { key: 'confirmed', label: 'Tasdiqlangan' },
  { key: 'all', label: 'Hammasi' },
]

export const STATUS_LABEL: Record<
  ReportStatus,
  { text: string; variant: 'secondary' | 'success' | 'destructive' }
> = {
  pending: { text: 'Kutilmoqda', variant: 'secondary' },
  confirmed: { text: 'Tasdiqlangan', variant: 'success' },
  rejected: { text: 'Rad etilgan', variant: 'destructive' },
}

export const TYPE_LABEL: Record<Report['report_type'], string> = {
  laboratory: 'Laboratoriya',
  visual: "Visual ko'rik",
  instrumental: "Instrumental ko'rik",
}

function ReportRow({ report }: { report: Report }) {
  const status = STATUS_LABEL[report.status]

  return (
    <Link
      to={`/reports/${report.id}`}
      className="flex items-center gap-3 border-b border-border px-4 py-3 last:border-0 active:bg-muted"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium">{report.author.full_name}</p>
          <Badge variant={status.variant}>{status.text}</Badge>
        </div>
        <p className="truncate text-sm text-muted-foreground">{report.customer_name}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {TYPE_LABEL[report.report_type]} &middot; {report.district.name_uz} &middot;{' '}
          {formatTime(report.created_at)}
        </p>
      </div>
      <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
    </Link>
  )
}

export function ReportsPage() {
  const [filter, setFilter] = useState<ReportStatus | 'all'>('pending')
  const [page, setPage] = useState(1)
  const [today] = useState(() => toApiDate(new Date()))

  const me = useMe()
  const isAdmin = me.data?.role === 'admin' || me.data?.role === 'superadmin'

  const reports = useReports({
    page,
    status: filter === 'all' ? undefined : filter,
    // Kutilayotganlar hamma kun bo'yicha, qolgan filtrlar bugungi kun bo'yicha
    day: filter === 'pending' ? undefined : today,
  })

  if (me.isLoading) return <LoadingScreen />
  if (me.error) return <ErrorScreen error={me.error} />

  return (
    <div>
      <header className="sticky top-0 z-10 border-b border-border bg-background px-4 pb-2 pt-3">
        <h1 className="text-lg font-semibold">
          {isAdmin ? 'Hisobotlar' : 'Mening hisobotlarim'}
        </h1>
        <div className="mt-2 flex gap-2 overflow-x-auto">
          {FILTERS.map(({ key, label }) => (
            <Button
              key={key}
              size="sm"
              variant={filter === key ? 'default' : 'secondary'}
              onClick={() => {
                setFilter(key)
                setPage(1)
              }}
            >
              {label}
            </Button>
          ))}
        </div>
      </header>

      {reports.isLoading ? (
        <div className="space-y-3 p-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : reports.error ? (
        <ErrorScreen error={reports.error} />
      ) : !reports.data || reports.data.items.length === 0 ? (
        <EmptyScreen
          title="Hisobot yo'q"
          description={
            filter === 'pending'
              ? "Tasdiqlash kutayotgan hisobotlar yo'q."
              : "Bu filtr bo'yicha hech nima topilmadi."
          }
        />
      ) : (
        <>
          <div className="animate-fade-in">
            {reports.data.items.map((report) => (
              <ReportRow key={report.id} report={report} />
            ))}
          </div>

          {reports.data.pages > 1 && (
            <div className="flex items-center justify-center gap-3 py-4">
              <Button
                size="sm"
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Oldingi
              </Button>
              <span className="text-sm text-muted-foreground">
                {reports.data.page}/{reports.data.pages}
              </span>
              <Button
                size="sm"
                variant="secondary"
                disabled={page >= reports.data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Keyingi
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
