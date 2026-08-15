import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from '@/App'
import { initTelegram } from '@/telegram/init'
import './index.css'

// SDK React dan oldin ishga tushiriladi: mavzu o'zgaruvchilari birinchi
// render paytida joyida bo'lishi kerak, aks holda ekran bir lahza oq bo'lib
// ko'rinadi.
initTelegram()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Mini App qisqa muddat ochiladi — ma'lumot tez eskiradi
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
