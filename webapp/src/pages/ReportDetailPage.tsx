import { Check, MapPin, X } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { Field } from '@/components/Field'
import { ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useMe, useReport, useReportDecision } from '@/lib/queries'
import { formatDateTime, mapsUrl } from '@/lib/utils'
import { STATUS_LABEL, TYPE_LABEL } from './ReportsPage'

export function ReportDetailPage() {
  const { id } = useParams<{ id: string }>()
  const reportId = Number(id)
  const navigate = useNavigate()

  const me = useMe()
  const report = useReport(reportId)
  const { approve, reject } = useReportDecision(reportId)

  if (report.isLoading || me.isLoading) return <LoadingScreen />
  if (report.error) return <ErrorScreen error={report.error} />
  if (!report.data) return <ErrorScreen error={new Error('Hisobot topilmadi')} />

  const data = report.data
  const status = STATUS_LABEL[data.status]
  const isAdmin = me.data?.role === 'admin' || me.data?.role === 'superadmin'
  const canDecide = isAdmin && data.status === 'pending'
  const busy = approve.isPending || reject.isPending
  const decisionError = approve.error ?? reject.error

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">{data.author.full_name}</h1>
          <p className="text-sm text-muted-foreground">{data.author.position}</p>
        </div>
        <Badge variant={status.variant}>{status.text}</Badge>
      </div>

      <Card>
        <CardContent className="pt-4">
          <Field label="Turi" value={TYPE_LABEL[data.report_type]} />
          <Field label="Hudud" value={data.district.name_uz} />
          <Field label="Buyurtmachi" value={data.customer_name} />
          {data.plots_count !== null && (
            <Field label="Uchastkalar" value={String(data.plots_count)} />
          )}
          <Field
            label="Sheriklar"
            value={
              data.partners.length > 0
                ? data.partners.map((p) => p.full_name).join(', ')
                : '—'
            }
          />
          <Field label="Sana" value={formatDateTime(data.created_at)} />
          <Field label="Rasmlar" value={`${data.photo_file_ids.length} ta`} />
        </CardContent>
      </Card>

      <Button variant="outline" className="w-full" asChild>
        <a
          href={mapsUrl(data.location.lat, data.location.lon)}
          target="_blank"
          rel="noreferrer"
        >
          <MapPin />
          Xaritada ochish
        </a>
      </Button>

      {decisionError && (
        <p className="text-sm text-destructive">
          {decisionError instanceof Error ? decisionError.message : 'Xatolik'}
        </p>
      )}

      {canDecide && (
        <div className="flex gap-3">
          <Button
            className="flex-1"
            disabled={busy}
            onClick={() => approve.mutate(undefined, { onSuccess: () => reject.reset() })}
          >
            <Check />
            Tasdiqlash
          </Button>
          <Button
            variant="destructive"
            className="flex-1"
            disabled={busy}
            onClick={() =>
              reject.mutate(undefined, {
                onSuccess: () => {
                  approve.reset()
                  navigate(-1)
                },
              })
            }
          >
            <X />
            Rad etish
          </Button>
        </div>
      )}
    </div>
  )
}
