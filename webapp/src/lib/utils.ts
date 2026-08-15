import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** shadcn/ui ning standart yordamchisi: shartli sinflar + Tailwind ziddiyatlarini yechish. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const TASHKENT = 'Asia/Tashkent'

/** ISO vaqtni Toshkent mintaqasida "05.06.2026 11:30" ko'rinishida beradi. */
export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    timeZone: TASHKENT,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
    .format(new Date(iso))
    .replace(',', '')
}

export function formatTime(iso: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    timeZone: TASHKENT,
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

/** API uchun YYYY-MM-DD (Toshkent kuni bo'yicha). */
export function toApiDate(date: Date): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TASHKENT }).format(date)
}

export function mapsUrl(lat: number, lon: number): string {
  return `https://maps.google.com/?q=${lat},${lon}`
}
