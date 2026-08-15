import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, useMemo, type ReactNode } from 'react'

import { ApiError, createApi, type Api, type ReportStatus } from './api'

const ApiContext = createContext<Api | null>(null)

export function ApiProvider({
  initData,
  children,
}: {
  initData: string
  children: ReactNode
}) {
  const api = useMemo(() => createApi(initData), [initData])
  return <ApiContext.Provider value={api}>{children}</ApiContext.Provider>
}

export function useApi(): Api {
  const api = useContext(ApiContext)
  if (!api) throw new Error('useApi ApiProvider ichida chaqirilishi kerak')
  return api
}

/**
 * Ruxsat va autentifikatsiya xatolarini qayta urinib ko'rish ma'nosiz —
 * javob o'zgarmaydi, faqat foydalanuvchi kutib qoladi.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
    return false
  }
  return failureCount < 2
}

export function useMe() {
  const api = useApi()
  return useQuery({ queryKey: ['me'], queryFn: () => api.getMe(), retry: shouldRetry })
}

export function useReports(params: { day?: string; status?: ReportStatus; page: number }) {
  const api = useApi()
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => api.listReports({ ...params, per_page: 20 }),
    retry: shouldRetry,
  })
}

export function useReport(id: number) {
  const api = useApi()
  return useQuery({
    queryKey: ['report', id],
    queryFn: () => api.getReport(id),
    retry: shouldRetry,
  })
}

export function useEmployees(page: number) {
  const api = useApi()
  return useQuery({
    queryKey: ['employees', page],
    queryFn: () => api.listEmployees({ page, per_page: 20 }),
    retry: shouldRetry,
  })
}

export function useReportDecision(id: number) {
  const api = useApi()
  const queryClient = useQueryClient()

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['report', id] })
    void queryClient.invalidateQueries({ queryKey: ['reports'] })
  }

  const approve = useMutation({
    mutationFn: () => api.approveReport(id),
    onSuccess: invalidate,
  })

  const reject = useMutation({
    mutationFn: () => api.rejectReport(id),
    onSuccess: invalidate,
  })

  return { approve, reject }
}
