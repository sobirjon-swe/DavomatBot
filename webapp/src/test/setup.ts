import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Har testdan keyin DOM tozalanadi, aks holda oldingi test qoldirgan
// elementlar keyingisida topilib, natijani chalg'itadi.
afterEach(() => {
  cleanup()
})

// jsdom da yo'q, lekin rasm ko'rinishini yaratishda ishlatiladi
if (!globalThis.URL.createObjectURL) {
  globalThis.URL.createObjectURL = () => 'blob:test'
  globalThis.URL.revokeObjectURL = () => {}
}
