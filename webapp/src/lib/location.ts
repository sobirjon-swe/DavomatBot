import { locationManager } from '@telegram-apps/sdk-react'

export interface Coordinates {
  lat: number
  lon: number
  /** Metrlarda, agar qurilma bersa */
  accuracy?: number
}

export type LocationErrorCode = 'denied' | 'unavailable' | 'timeout'

export class LocationError extends Error {
  constructor(
    readonly code: LocationErrorCode,
    message: string,
  ) {
    super(message)
    this.name = 'LocationError'
  }
}

/** Telegram sozlamalarini ochish (ruxsat rad etilgan bo'lsa). */
export function canOpenLocationSettings(): boolean {
  return locationManager.openSettings.isAvailable()
}

export function openLocationSettings(): void {
  if (locationManager.openSettings.isAvailable()) {
    locationManager.openSettings()
  }
}

function pick(raw: unknown): Coordinates | null {
  if (!raw || typeof raw !== 'object') return null
  const data = raw as Record<string, unknown>

  // SDK bu qiymatni tiplamaydi va mijoz versiyasiga qarab maydon nomi
  // farq qilishi mumkin, shuning uchun ikkala shakl ham tekshiriladi.
  const lat = data.latitude ?? data.lat
  const lon = data.longitude ?? data.lon
  const accuracy = data.horizontalAccuracy ?? data.horizontal_accuracy

  if (typeof lat !== 'number' || typeof lon !== 'number') return null
  return {
    lat,
    lon,
    accuracy: typeof accuracy === 'number' ? accuracy : undefined,
  }
}

async function fromTelegram(): Promise<Coordinates | null> {
  if (!locationManager.mount.isAvailable()) return null

  try {
    if (!locationManager.isMounted()) {
      await locationManager.mount()
    }
    if (!locationManager.requestLocation.isAvailable()) return null

    return pick(await locationManager.requestLocation())
  } catch (error) {
    // Ruxsat aniq rad etilgan bo'lsa buni brauzer zaxira yo'liga
    // yashirmaymiz — aks holda foydalanuvchi "Sozlamalarni ochish"
    // tugmasini ko'rmay, umumiy "aniqlab bo'lmadi" xabarini ko'radi.
    if (locationManager.isAccessRequested() && !locationManager.isAccessGranted()) {
      throw new LocationError('denied', "Joylashuvga ruxsat berilmadi")
    }
    // Boshqa sabab (qo'llab-quvvatlanmaydi, band va h.k.) — brauzerga o'tamiz
    void error
    return null
  }
}

function fromBrowser(): Promise<Coordinates> {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new LocationError('unavailable', 'Qurilma joylashuvni bermayapti'))
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
          accuracy: position.coords.accuracy,
        }),
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          reject(new LocationError('denied', 'Joylashuvga ruxsat berilmadi'))
        } else if (error.code === error.TIMEOUT) {
          reject(
            new LocationError('timeout', 'Joylashuv aniqlanmadi, qayta urinib ko‘ring'),
          )
        } else {
          reject(new LocationError('unavailable', 'Joylashuvni aniqlab bo‘lmadi'))
        }
      },
      { enableHighAccuracy: true, timeout: 20_000, maximumAge: 0 },
    )
  })
}

/**
 * Joylashuvni oladi.
 *
 * Avval Telegramning LocationManager i sinaladi (Bot API 8.0+), keyin
 * brauzer geolokatsiyasi. Ikkalasi ham ishlamasa xato ko'tariladi va
 * foydalanuvchiga hisobotni bot orqali yuborish taklif qilinadi —
 * chatdagi "joylashuvni yuborish" tugmasi hamma mijozlarda ishlaydi.
 */
export async function getCurrentLocation(): Promise<Coordinates> {
  const fromApp = await fromTelegram()
  if (fromApp) return fromApp
  return fromBrowser()
}
