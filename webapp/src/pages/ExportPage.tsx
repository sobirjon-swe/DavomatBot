import { useCallback, useState } from 'react'

import { Section } from '@/components/Section'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { useExportReports } from '@/lib/queries'
import { toApiDate } from '@/lib/utils'
import { useMainButton } from '@/telegram/mainButton'

type Range = 'today' | 'week' | 'month' | 'custom'

const RANGE_LABEL: Record<Range, string> = {
  today: 'Bugun',
  week: 'Shu hafta',
  month: 'Shu oy',
  custom: "O'zi tanlash",
}

function rangeFor(range: Range, customFrom: string, customTo: string): [string, string] {
  const today = new Date()
  if (range === 'custom') return [customFrom, customTo]
  if (range === 'today') return [toApiDate(today), toApiDate(today)]
  if (range === 'week') {
    const day = (today.getDay() + 6) % 7 // dushanba = 0
    const start = new Date(today)
    start.setDate(today.getDate() - day)
    return [toApiDate(start), toApiDate(today)]
  }
  const start = new Date(today.getFullYear(), today.getMonth(), 1)
  return [toApiDate(start), toApiDate(today)]
}

/**
 * Fayl to'g'ridan-to'g'ri Mini App'da yuklab olinmaydi — Telegram WebView'da
 * bu ishonchsiz. O'rniga tayyor Excel fayl botning o'zi orqali adminning
 * shaxsiy chatiga yuboriladi (botdagi "Eksport" menyusi bilan bir xil natija).
 */
export function ExportPage() {
  const exportReports = useExportReports()

  const [range, setRange] = useState<Range>('today')
  const today = toApiDate(new Date())
  const [customFrom, setCustomFrom] = useState(today)
  const [customTo, setCustomTo] = useState(today)

  const canSubmit =
    !exportReports.isPending && (range !== 'custom' || (customFrom && customTo))

  const submit = useCallback(() => {
    if (!canSubmit) return
    const [date_from, date_to] = rangeFor(range, customFrom, customTo)
    exportReports.mutate({ date_from, date_to })
  }, [canSubmit, range, customFrom, customTo, exportReports])

  useMainButton({
    text: exportReports.isPending ? 'Yuborilmoqda...' : 'Botga yuborish',
    isEnabled: Boolean(canSubmit),
    isLoaderVisible: exportReports.isPending,
    onClick: submit,
  })

  const error = exportReports.error
  const errorMessage =
    error instanceof ApiError
      ? error.code === 'empty'
        ? "Bu oraliqda hisobot topilmadi"
        : error.message
      : error
        ? 'Xatolik yuz berdi'
        : null

  return (
    <div className="space-y-6 p-4 pb-8">
      <div>
        <h1 className="text-lg font-semibold">Eksport</h1>
        <p className="text-sm text-muted-foreground">
          Tanlangan oraliqdagi hisobotlar Excel fayl qilib botdagi shaxsiy
          chatingizga yuboriladi.
        </p>
      </div>

      <Section title="Oraliq">
        <div className="flex flex-col gap-2">
          {(Object.keys(RANGE_LABEL) as Range[]).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setRange(key)}
              className={`flex items-center justify-between rounded-md border px-3 py-2 text-left text-sm ${
                range === key ? 'border-primary bg-primary/10' : 'border-border'
              }`}
            >
              {RANGE_LABEL[key]}
            </button>
          ))}
        </div>
      </Section>

      {range === 'custom' && (
        <Section title="Sanalar">
          <div className="flex items-center gap-2">
            <Input
              type="date"
              value={customFrom}
              max={customTo}
              onChange={(event) => setCustomFrom(event.target.value)}
            />
            <span className="text-muted-foreground">—</span>
            <Input
              type="date"
              value={customTo}
              min={customFrom}
              max={today}
              onChange={(event) => setCustomTo(event.target.value)}
            />
          </div>
        </Section>
      )}

      {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

      {exportReports.isSuccess && (
        <p className="text-sm text-primary">
          Fayl botga yuborildi — Telegram'dagi bot chatini tekshiring.
        </p>
      )}
    </div>
  )
}
