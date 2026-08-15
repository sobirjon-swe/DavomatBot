import { mainButton } from '@telegram-apps/sdk-react'
import { useEffect, useRef } from 'react'

interface Params {
  text: string
  isEnabled: boolean
  isLoaderVisible?: boolean
  onClick: () => void
}

/** Telegram MainButton mavjudmi (eski mijozlarda va brauzerda yo'q). */
export function hasMainButton(): boolean {
  return mainButton.mount.isAvailable() || mainButton.isMounted()
}

/**
 * Ekran pastidagi tizim tugmasini boshqaradi.
 *
 * Telegramda bu tugma klaviatura ustida turadi va sahifa bilan birga
 * siljimaydi — forma yuborish uchun undan qulayrog'i yo'q.
 */
export function useMainButton({ text, isEnabled, isLoaderVisible, onClick }: Params): void {
  // Har renderga yangi funksiya kelmasligi uchun ref: aks holda obuna
  // doimiy qayta yozilib turadi.
  const handler = useRef(onClick)
  handler.current = onClick

  useEffect(() => {
    if (!mainButton.mount.isAvailable() || mainButton.isMounted()) return
    mainButton.mount()
  }, [])

  useEffect(() => {
    if (!mainButton.setParams.isAvailable()) return

    mainButton.setParams({
      text,
      isVisible: true,
      isEnabled,
      isLoaderVisible: Boolean(isLoaderVisible),
    })

    return () => {
      // Boshqa ekranga o'tganda tugma qolib ketmasin
      if (mainButton.setParams.isAvailable()) {
        mainButton.setParams({ isVisible: false, isLoaderVisible: false })
      }
    }
  }, [text, isEnabled, isLoaderVisible])

  useEffect(() => {
    if (!mainButton.onClick.isAvailable()) return
    return mainButton.onClick(() => handler.current())
  }, [])
}
