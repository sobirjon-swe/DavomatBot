import { Check } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Section } from '@/components/Section'
import { ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { Input } from '@/components/ui/input'
import { useCreateEmployee, useDistricts } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { useMainButton } from '@/telegram/mainButton'

export function NewEmployeePage() {
  const navigate = useNavigate()
  const districts = useDistricts()
  const createEmployee = useCreateEmployee()

  const [fullName, setFullName] = useState('')
  const [position, setPosition] = useState('')
  const [districtIds, setDistrictIds] = useState<number[]>([])

  const missing = useMemo(() => {
    const items: string[] = []
    if (!fullName.trim()) items.push('ism')
    if (!position.trim()) items.push('lavozim')
    if (districtIds.length === 0) items.push('hudud')
    return items
  }, [fullName, position, districtIds])

  const canSubmit = missing.length === 0 && !createEmployee.isPending

  function toggleDistrict(id: number) {
    setDistrictIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id],
    )
  }

  const submit = useCallback(() => {
    if (!canSubmit) return

    createEmployee.mutate(
      {
        full_name: fullName.trim(),
        position: position.trim(),
        district_ids: districtIds,
      },
      {
        onSuccess: (employee) => navigate(`/employees/${employee.id}`, { replace: true }),
      },
    )
  }, [canSubmit, fullName, position, districtIds, createEmployee, navigate])

  useMainButton({
    text: createEmployee.isPending ? 'Qo’shilmoqda...' : 'Qo’shish',
    isEnabled: canSubmit,
    isLoaderVisible: createEmployee.isPending,
    onClick: submit,
  })

  if (districts.isLoading) return <LoadingScreen />
  if (districts.error) return <ErrorScreen error={districts.error} />

  return (
    <div className="space-y-6 p-4 pb-8">
      <h1 className="text-lg font-semibold">Yangi hodim</h1>

      <Section title="Ism va familiya">
        <Input
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          placeholder="Ism Familiya"
          maxLength={255}
        />
      </Section>

      <Section title="Lavozim">
        <Input
          value={position}
          onChange={(event) => setPosition(event.target.value)}
          placeholder="Masalan, muhandis"
          maxLength={255}
        />
      </Section>

      <Section title="Hududlar" hint="Kamida bitta hudud tanlang">
        <div className="flex flex-col gap-2">
          {(districts.data ?? []).map((district) => {
            const selected = districtIds.includes(district.id)
            return (
              <button
                key={district.id}
                type="button"
                onClick={() => toggleDistrict(district.id)}
                className={cn(
                  'flex items-center justify-between rounded-md border px-3 py-2 text-left text-sm',
                  selected ? 'border-primary bg-primary/10' : 'border-border',
                )}
              >
                {district.name_uz}
                {selected && <Check className="size-4 text-primary" />}
              </button>
            )
          })}
        </div>
      </Section>

      {createEmployee.error && (
        <p className="text-sm text-destructive">
          {createEmployee.error instanceof Error
            ? createEmployee.error.message
            : 'Qo’shishda xatolik'}
        </p>
      )}
    </div>
  )
}
