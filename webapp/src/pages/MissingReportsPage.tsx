import { useState } from 'react'

import { EmptyScreen, ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { Input } from '@/components/ui/input'
import { useMissingReports } from '@/lib/queries'
import { toApiDate } from '@/lib/utils'

/** Botning "⚠️ Bermaganlar" bo'limi bilan bir xil — berilgan kunda hisobot
 * bermagan faol hodimlar (sheriklar hisobga olinadi, kunni tanlash mumkin). */
export function MissingReportsPage() {
  const [day, setDay] = useState(() => toApiDate(new Date()))
  const missing = useMissingReports(day)

  return (
    <div className="space-y-4 p-4">
      <header>
        <h1 className="text-lg font-semibold">Hisobot bermaganlar</h1>
        <p className="text-sm text-muted-foreground">
          Tanlangan kunda hisobotda umuman qatnashmagan hodimlar (sherik sifatida
          qo'shilgan bo'lsa ham hisobga olinadi).
        </p>
      </header>

      <Input
        type="date"
        value={day}
        onChange={(event) => setDay(event.target.value)}
        max={toApiDate(new Date())}
      />

      {missing.isLoading ? (
        <LoadingScreen />
      ) : missing.error ? (
        <ErrorScreen error={missing.error} />
      ) : !missing.data || missing.data.length === 0 ? (
        <EmptyScreen
          title="Hammasi topshirilgan"
          description="Tanlangan kunda hisobot bermagan hodim yo'q."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          {missing.data.map((employee) => (
            <div
              key={employee.id}
              className="flex items-center justify-between border-b border-border px-4 py-3 last:border-0"
            >
              <div>
                <p className="font-medium">{employee.full_name}</p>
                <p className="text-sm text-muted-foreground">{employee.position}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
