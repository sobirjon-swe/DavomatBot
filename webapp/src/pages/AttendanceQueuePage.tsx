import { Check, MapPin, X } from 'lucide-react'

import { Field } from '@/components/Field'
import { EmptyScreen, ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useReportDecision, useReports } from '@/lib/queries'
import { formatDateTime, mapsUrl } from '@/lib/utils'
import { TYPE_LABEL } from './ReportsPage'

/**
 * Botning "✅ Davomat tasdiqlash" navbatiga o'xshaydi: bir vaqtning o'zida
 * bitta kutilayotgan hisobot ko'rsatiladi. Tasdiqlash/rad etishdan keyin
 * qo'lda "keyingisiga" o'tish shart emas — mutatsiya `reports` so'rovini
 * eskirgan deb belgilaydi, ro'yxat qayta yuklanadi va navbatning yangi
 * boshi (endi tasdiqlangan/rad etilgani olib tashlangan holda) o'z-o'zidan
 * shu yerda ko'rinadi.
 */
export function AttendanceQueuePage() {
  const reports = useReports({ status: 'pending', page: 1 })
  const current = reports.data?.items[0]
  const { approve, reject } = useReportDecision(current?.id ?? 0)

  if (reports.isLoading) return <LoadingScreen />
  if (reports.error) return <ErrorScreen error={reports.error} />

  const total = reports.data?.total ?? 0

  return (
    <div className="space-y-4 p-4">
      <header>
        <h1 className="text-lg font-semibold">Davomat tasdiqlash</h1>
        <p className="text-sm text-muted-foreground">
          {total > 0 ? `Kutilmoqda: ${total} ta` : 'Tasdiqlash kutayotgan hisobotlar yo\'q'}
        </p>
      </header>

      {!current ? (
        <EmptyScreen
          title="Tasdiqlanmagan hisobotlar yo'q"
          description="Hammasi ko'rib chiqilgan."
        />
      ) : (
        <>
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">{current.author.full_name}</h2>
              <p className="text-sm text-muted-foreground">{current.author.position}</p>
            </div>
          </div>

          <Card>
            <CardContent className="pt-4">
              <Field label="Turi" value={TYPE_LABEL[current.report_type]} />
              <Field label="Hudud" value={current.district.name_uz} />
              <Field label="Buyurtmachi" value={current.customer_name} />
              {current.plots_count !== null && (
                <Field label="Uchastkalar" value={String(current.plots_count)} />
              )}
              <Field
                label="Sheriklar"
                value={
                  current.partners.length > 0
                    ? current.partners.map((p) => p.full_name).join(', ')
                    : '—'
                }
              />
              <Field label="Sana" value={formatDateTime(current.created_at)} />
              <Field label="Rasmlar" value={`${current.photo_file_ids.length} ta`} />
            </CardContent>
          </Card>

          <Button variant="outline" className="w-full" asChild>
            <a
              href={mapsUrl(current.location.lat, current.location.lon)}
              target="_blank"
              rel="noreferrer"
            >
              <MapPin />
              Xaritada ochish
            </a>
          </Button>

          {(approve.error || reject.error) && (
            <p className="text-sm text-destructive">
              Amalni bajarishda xatolik yuz berdi.
            </p>
          )}

          <div className="flex gap-3">
            <Button
              className="flex-1"
              disabled={approve.isPending || reject.isPending}
              onClick={() => approve.mutate(undefined, { onSuccess: () => reject.reset() })}
            >
              <Check />
              Tasdiqlash
            </Button>
            <Button
              variant="destructive"
              className="flex-1"
              disabled={approve.isPending || reject.isPending}
              onClick={() => reject.mutate(undefined, { onSuccess: () => approve.reset() })}
            >
              <X />
              Rad etish
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
