import { ChevronRight, Download, Search, UserX, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyScreen, ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import type { Report, ReportStatus } from '@/lib/api'
import { useColleagues, useMe, useReports } from '@/lib/queries'
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

interface Search {
  date: string
  userId: number
  userName: string
}

function SearchPanel({
  onSearch,
  onClose,
}: {
  onSearch: (search: Search) => void
  onClose: () => void
}) {
  const colleagues = useColleagues()
  const [date, setDate] = useState(() => toApiDate(new Date()))
  const [userId, setUserId] = useState<number | ''>('')

  const employees = colleagues.data ?? []
  const canSearch = date !== '' && userId !== ''

  return (
    <div className="mt-2 space-y-2 rounded-md border border-border p-3">
      <div className="flex gap-2">
        <Input
          type="date"
          value={date}
          max={toApiDate(new Date())}
          onChange={(event) => setDate(event.target.value)}
        />
        <Select
          value={userId}
          onChange={(event) => setUserId(event.target.value ? Number(event.target.value) : '')}
        >
          <option value="">Hodim</option>
          {employees.map((employee) => (
            <option key={employee.id} value={employee.id}>
              {employee.full_name}
            </option>
          ))}
        </Select>
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          className="flex-1"
          disabled={!canSearch}
          onClick={() => {
            if (!canSearch) return
            const employee = employees.find((e) => e.id === userId)
            onSearch({ date, userId, userName: employee?.full_name ?? '' })
          }}
        >
          <Search />
          Qidirish
        </Button>
        <Button size="sm" variant="secondary" onClick={onClose}>
          Bekor qilish
        </Button>
      </div>
    </div>
  )
}

export function ReportsPage() {
  const [filter, setFilter] = useState<ReportStatus | 'all'>('pending')
  const [page, setPage] = useState(1)
  const [today] = useState(() => toApiDate(new Date()))
  const [search, setSearch] = useState<Search | null>(null)
  const [searchOpen, setSearchOpen] = useState(false)

  const me = useMe()
  const isAdmin = me.data?.role === 'admin' || me.data?.role === 'superadmin'

  const reports = useReports(
    search
      ? { page, day: search.date, user_id: search.userId }
      : {
          page,
          status: filter === 'all' ? undefined : filter,
          // Kutilayotganlar hamma kun bo'yicha, qolgan filtrlar bugungi kun bo'yicha
          day: filter === 'pending' ? undefined : today,
        },
  )

  if (me.isLoading) return <LoadingScreen />
  if (me.error) return <ErrorScreen error={me.error} />

  return (
    <div>
      <header className="sticky top-0 z-10 border-b border-border bg-background px-4 pb-2 pt-3">
        <h1 className="text-lg font-semibold">
          {isAdmin ? 'Hisobotlar' : 'Mening hisobotlarim'}
        </h1>

        {!search && (
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
        )}

        {isAdmin && !search && (
          <div className="mt-2 flex gap-2 overflow-x-auto">
            <Button size="sm" variant="secondary" onClick={() => setSearchOpen((v) => !v)}>
              <Search />
              Qidiruv
            </Button>
            <Button size="sm" variant="secondary" asChild>
              <Link to="/missing">
                <UserX />
                Bermaganlar
              </Link>
            </Button>
            <Button size="sm" variant="secondary" asChild>
              <Link to="/export">
                <Download />
                Eksport
              </Link>
            </Button>
          </div>
        )}

        {!isAdmin ? null : search ? (
          <div className="mt-2 flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
            <span>
              {search.userName} &middot; {search.date}
            </span>
            <button
              type="button"
              onClick={() => {
                setSearch(null)
                setPage(1)
              }}
              className="text-muted-foreground"
              aria-label="Qidiruvni tozalash"
            >
              <X className="size-4" />
            </button>
          </div>
        ) : (
          searchOpen && (
            <SearchPanel
              onSearch={(value) => {
                setSearch(value)
                setSearchOpen(false)
                setPage(1)
              }}
              onClose={() => setSearchOpen(false)}
            />
          )
        )}
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
