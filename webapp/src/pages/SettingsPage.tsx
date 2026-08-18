import { useCallback, useMemo, useState } from 'react'

import { Section } from '@/components/Section'
import { LoadingScreen } from '@/components/StatusScreen'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { useChangeAccessPassword, useChangeLanguage, useMe } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { useMainButton } from '@/telegram/mainButton'

const MIN_PASSWORD_LENGTH = 6

const LANGUAGES: { code: 'uz' | 'ru'; label: string }[] = [
  { code: 'uz', label: "O'zbekcha" },
  { code: 'ru', label: 'Русский' },
]

function LanguageSection({ current }: { current: string }) {
  const changeLanguage = useChangeLanguage()

  return (
    <Section title="Til / Язык">
      <div className="flex gap-2">
        {LANGUAGES.map(({ code, label }) => (
          <button
            key={code}
            type="button"
            disabled={changeLanguage.isPending}
            onClick={() => changeLanguage.mutate(code)}
            className={cn(
              'flex-1 rounded-md border px-3 py-2 text-sm',
              current === code ? 'border-primary bg-primary/10' : 'border-border',
            )}
          >
            {label}
          </button>
        ))}
      </div>
    </Section>
  )
}

/**
 * Bu yerdagi parol — shaxsiy hisob paroli emas, botga yangi hodim/admin
 * bo'lib ro'yxatdan o'tishda so'raladigan umumiy kirish paroli. Botning
 * "🔑 Parolni o'zgartirish" menyusi bilan bir xil qiymatni boshqaradi.
 */
function AccessPasswordSection() {
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
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold">Kirish parolini almashtirish</h2>
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

export function SettingsPage() {
  const me = useMe()

  if (me.isLoading || !me.data) return <LoadingScreen />

  const isAdmin = me.data.role === 'admin' || me.data.role === 'superadmin'

  return (
    <div className="space-y-8 p-4 pb-8">
      <h1 className="text-lg font-semibold">Sozlamalar</h1>

      <LanguageSection current={me.data.language} />

      {isAdmin && (
        <>
          <div className="border-t border-border" />
          <AccessPasswordSection />
        </>
      )}
    </div>
  )
}
