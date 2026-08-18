import { Check, Pencil, ShieldOff, UserCog, UserX } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'

import { Field } from '@/components/Field'
import { Section } from '@/components/Section'
import { ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Role } from '@/lib/api'
import { useDistricts, useEmployee, useEmployeeActions, useMe } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { useMainButton } from '@/telegram/mainButton'

const ROLE_LABEL: Record<Role, string> = {
  superadmin: 'Super admin',
  admin: 'Admin',
  employee: 'Hodim',
}

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const employeeId = Number(id)

  const me = useMe()
  const employee = useEmployee(employeeId)
  const districts = useDistricts()
  const { update, deactivate, activate, changeRole } = useEmployeeActions(employeeId)

  const [editing, setEditing] = useState(false)
  const [fullName, setFullName] = useState('')
  const [position, setPosition] = useState('')
  const [districtIds, setDistrictIds] = useState<number[]>([])

  // Ma'lumot kelgach forma boshlang'ich qiymatlarini oladi
  useEffect(() => {
    if (!employee.data) return
    setFullName(employee.data.full_name)
    setPosition(employee.data.position)
    setDistrictIds(employee.data.districts.map((d) => d.id))
  }, [employee.data])

  const missing = useMemo(() => {
    const items: string[] = []
    if (!fullName.trim()) items.push('ism')
    if (!position.trim()) items.push('lavozim')
    if (districtIds.length === 0) items.push('hudud')
    return items
  }, [fullName, position, districtIds])

  const canSave = missing.length === 0 && !update.isPending

  function toggleDistrict(districtId: number) {
    setDistrictIds((prev) =>
      prev.includes(districtId) ? prev.filter((d) => d !== districtId) : [...prev, districtId],
    )
  }

  const save = useCallback(() => {
    if (!canSave) return
    update.mutate(
      { full_name: fullName.trim(), position: position.trim(), district_ids: districtIds },
      { onSuccess: () => setEditing(false) },
    )
  }, [canSave, fullName, position, districtIds, update])

  useMainButton({
    text: update.isPending ? 'Saqlanmoqda...' : 'Saqlash',
    isEnabled: editing && canSave,
    isLoaderVisible: update.isPending,
    onClick: save,
  })

  if (me.isLoading || employee.isLoading || districts.isLoading) return <LoadingScreen />
  if (me.error) return <ErrorScreen error={me.error} />
  if (employee.error) return <ErrorScreen error={employee.error} />
  if (districts.error) return <ErrorScreen error={districts.error} />
  if (!employee.data || !me.data) return null

  const target = employee.data
  const isSuperadmin = me.data.role === 'superadmin'
  const isSelf = me.data.id === target.id
  const busy = deactivate.isPending || activate.isPending || changeRole.isPending

  if (editing) {
    return (
      <div className="space-y-6 p-4 pb-8">
        <h1 className="text-lg font-semibold">Hodimni tahrirlash</h1>

        <Section title="Ism va familiya">
          <Input value={fullName} onChange={(e) => setFullName(e.target.value)} maxLength={255} />
        </Section>

        <Section title="Lavozim">
          <Input value={position} onChange={(e) => setPosition(e.target.value)} maxLength={255} />
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

        {update.error && (
          <p className="text-sm text-destructive">
            {update.error instanceof Error ? update.error.message : 'Saqlashda xatolik'}
          </p>
        )}

        <Button variant="secondary" className="w-full" onClick={() => setEditing(false)}>
          Bekor qilish
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">{target.full_name}</h1>
          <p className="text-sm text-muted-foreground">{target.position}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge variant={target.role === 'employee' ? 'secondary' : 'outline'}>
            {ROLE_LABEL[target.role]}
          </Badge>
          {!target.is_active && <Badge variant="destructive">Faolsiz</Badge>}
        </div>
      </div>

      <div className="rounded-lg border border-border px-4">
        <Field label="Holat" value={target.is_active ? 'Faol' : 'Faolsizlantirilgan'} />
        <Field label="Botga kirgan" value={target.is_linked ? 'Ha' : "Yo'q"} />
        <Field
          label="Hududlar"
          value={target.districts.length > 0 ? target.districts.map((d) => d.name_uz).join(', ') : '—'}
        />
        <Field label="Qo'shilgan" value={new Date(target.created_at).toLocaleDateString('uz-UZ')} />
      </div>

      <Button variant="outline" className="w-full" onClick={() => setEditing(true)}>
        <Pencil />
        Tahrirlash
      </Button>

      {isSuperadmin && !isSelf && target.role !== 'superadmin' && (
        <>
          <Button
            variant="outline"
            className="w-full"
            disabled={busy}
            onClick={() => changeRole.mutate(target.role === 'admin' ? 'employee' : 'admin')}
          >
            <UserCog />
            {target.role === 'admin' ? 'Hodim qilish' : 'Admin qilish'}
          </Button>

          <Button
            variant={target.is_active ? 'destructive' : 'default'}
            className="w-full"
            disabled={busy}
            onClick={() =>
              target.is_active ? deactivate.mutate() : activate.mutate()
            }
          >
            {target.is_active ? <UserX /> : <ShieldOff />}
            {target.is_active ? 'Faolsizlantirish' : 'Tiklash'}
          </Button>
        </>
      )}

      {(changeRole.error || deactivate.error || activate.error) && (
        <p className="text-sm text-destructive">Amalni bajarishda xatolik yuz berdi.</p>
      )}
    </div>
  )
}
