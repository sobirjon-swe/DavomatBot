/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API manzili. Bo'sh bo'lsa so'rovlar shu domenga ketadi (nginx proxy). */
  readonly VITE_API_URL?: string
  /**
   * Faqat lokal ishlab chiqish uchun: qurilmadan nusxa olingan initData.
   * Prodda ishlatilmaydi — Telegram uni o'zi beradi.
   */
  readonly VITE_DEV_INIT_DATA?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
