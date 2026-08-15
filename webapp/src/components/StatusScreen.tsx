import { AlertCircle, Ban, Loader2, UserPlus } from 'lucide-react'
import type { ReactNode } from 'react'

import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

function Screen({
  icon,
  title,
  description,
  children,
  className,
}: {
  icon: ReactNode
  title: string
  description?: string
  children?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex min-h-[60vh] flex-col items-center justify-center gap-3 px-8 text-center',
        className,
      )}
    >
      {icon && <div className="text-muted-foreground">{icon}</div>}
      <p className="font-medium">{title}</p>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
      {children}
    </div>
  )
}

export function LoadingScreen() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Loader2 className="size-6 animate-spin text-muted-foreground" />
    </div>
  )
}

export function EmptyScreen({
  title,
  description,
}: {
  title: string
  description?: string
}) {
  return <Screen icon={null} title={title} description={description} />
}

/**
 * Xatoni foydalanuvchi tushunadigan ekranga aylantiradi.
 *
 * `not_registered` alohida ishlanadi: bu xato emas, shunchaki hodim hali
 * botda ro'yxatdan o'tmagan — unga nima qilish kerakligi aytiladi.
 */
export function ErrorScreen({ error }: { error: unknown }) {
  if (error instanceof ApiError && error.isNotRegistered) {
    return (
      <Screen
        icon={<UserPlus className="size-8" />}
        title="Avval botda ro'yxatdan o'ting"
        description="Botga qayting va /start buyrug'ini yuboring. Shundan keyin bu bo'lim ochiladi."
      />
    )
  }

  if (error instanceof ApiError && error.isDeactivated) {
    return (
      <Screen
        icon={<Ban className="size-8" />}
        title="Hisobingiz faolsizlantirilgan"
        description="Admin bilan bog'laning."
      />
    )
  }

  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : "Noma'lum xatolik"

  return (
    <Screen
      icon={<AlertCircle className="size-8" />}
      title="Xatolik"
      description={message}
    />
  )
}
