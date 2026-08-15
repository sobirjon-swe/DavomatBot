import {
  backButton,
  init as initSdk,
  miniApp,
  themeParams,
  viewport,
} from '@telegram-apps/sdk-react'

/**
 * SDK ni ishga tushiradi va Telegram mavzusini CSS o'zgaruvchilariga bog'laydi.
 *
 * `bindCssVars` --tg-theme-bg-color kabi o'zgaruvchilarni hujjatga qo'yadi;
 * index.css ularni ilova tokenlariga ulaydi. Shu tufayli ilova
 * foydalanuvchining kunduzgi/tungi rejimiga o'zi moslashadi.
 */
export function initTelegram(): void {
  initSdk()

  if (themeParams.mountSync.isAvailable()) {
    themeParams.mountSync()
    if (themeParams.bindCssVars.isAvailable()) {
      themeParams.bindCssVars()
    }
  }

  if (miniApp.mountSync.isAvailable()) {
    miniApp.mountSync()
    if (miniApp.bindCssVars.isAvailable()) {
      miniApp.bindCssVars()
    }
  }

  if (backButton.mount.isAvailable()) {
    backButton.mount()
  }

  // Viewport asinxron: xavfsiz zona (safe area) qiymatlari keyinroq keladi.
  if (viewport.mount.isAvailable()) {
    viewport
      .mount()
      .then(() => {
        if (viewport.bindCssVars.isAvailable()) {
          viewport.bindCssVars()
        }
        if (viewport.expand.isAvailable()) {
          viewport.expand()
        }
      })
      .catch(() => {
        // Eski mijozlarda viewport bo'lmasligi mumkin — ilova baribir ishlaydi
      })
  }

  if (miniApp.ready.isAvailable()) {
    miniApp.ready()
  }
}

/** Telegram muhitida ochilganmi (brauzerda initData bo'lmaydi). */
export function isInsideTelegram(): boolean {
  return Boolean((window as { Telegram?: { WebApp?: unknown } }).Telegram?.WebApp)
}
