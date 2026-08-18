import { useCallback, useMemo, useState } from 'react'

import { Section } from '@/components/Section'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { useChangeAccessPassword } from '@/lib/queries'
import { useMainButton } from '@/telegram/mainButton'

const MIN_PASSWORD_LENGTH = 6

/**
 * Bu yerdagi parol — shaxsiy hisob paroli emas, botga yangi hodim/admin
 * bo'lib ro'yxatdan o'tishda so'raladigan umumiy kirish paroli. Botning
 * "🔑 Parolni o'zgartirish" menyusi bilan bir xil qiymatni boshqaradi.
 */
export function SettingsPage() {
  const changePassword = useChangeAccessPassword()

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')

  const missing = useMemo(() => {
    const items: string[] = []
    if (!current) items.push('joriy parol')
    if (next.length < MIN_PASSWORD_LENGTH) items.push('yangi parol')
    if (confirm !== next) items.push('tasdiqlash')
    return items
  }, [current, next, confirm])

  const canSubmit = missing.length === 0 && !changePassword.isPending

  const submit = useCallback(() => {
    if (!canSubmit) return
    changePassword.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          setCurrent('')
          setNext('')
          setConfirm('')
        },
      },
    )
  }, [canSubmit, current, next, changePassword])

  useMainButton({
    text: changePassword.isPending ? 'Saqlanmoqda...' : 'Saqlash',
    isEnabled: canSubmit,
    isLoaderVisible: changePassword.isPending,
    onClick: submit,
  })

  const error = changePassword.error
  const errorMessage =
    error instanceof ApiError
      ? error.code === 'wrong_current_password'
        ? "Joriy parol noto'g'ri"
        : error.message
      : error
        ? 'Xatolik yuz berdi'
        : null

  return (
    <div className="space-y-6 p-4 pb-8">
      <div>
        <h1 className="text-lg font-semibold">Kirish parolini almashtirish</h1>
        <p className="text-sm text-muted-foreground">
          Bu — yangi hodim/admin ro'yxatdan o'tishda so'raladigan umumiy parol.
        </p>
      </div>

      <Section title="Joriy parol">
        <Input
          type="password"
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
          autoComplete="off"
        />
      </Section>

      <Section title="Yangi parol" hint={`Kamida ${MIN_PASSWORD_LENGTH} ta belgi`}>
        <Input
          type="password"
          value={next}
          onChange={(event) => setNext(event.target.value)}
          autoComplete="off"
        />
      </Section>

      <Section title="Yangi parolni tasdiqlash">
        <Input
          type="password"
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
          autoComplete="off"
        />
      </Section>

      {confirm.length > 0 && confirm !== next && (
        <p className="text-sm text-destructive">Parollar mos kelmadi</p>
      )}

      {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

      {changePassword.isSuccess && (
        <p className="text-sm text-primary">Parol muvaffaqiyatli almashtirildi.</p>
      )}
    </div>
  )
}
