/**
 * API mijozi.
 *
 * Har bir so'rovda Telegram bergan initData yuboriladi — server uni HMAC
 * bilan qayta tekshiradi. Alohida sessiya tokeni yo'q, shuning uchun bu
 * yerda saqlanadigan maxfiy narsa ham yo'q.
 *
 * Tiplar bot/api/schemas.py bilan mos bo'lishi kerak.
 */

const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export type Role = 'employee' | 'admin' | 'superadmin'
export type ReportStatus = 'pending' | 'confirmed' | 'rejected'

export interface District {
  id: number
  name_uz: string
  name_ru: string
}

export interface UserBrief {
  id: number
  full_name: string
  position: string
}

export interface User extends UserBrief {
  role: Role
  language: string
  is_active: boolean
  is_linked: boolean
  created_at: string
  districts: District[]
}

export interface Report {
  id: number
  author: UserBrief
  report_type: 'laboratory' | 'visual' | 'instrumental'
  district: District
  customer_name: string
  location: { lat: number; lon: number }
  plots_count: number | null
  partners: UserBrief[]
  photo_file_ids: string[]
  status: ReportStatus
  created_at: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  pages: number
}

/** Serverdan kelgan xato. `code` bo'yicha UI qaror qabul qiladi. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }

  get isNotRegistered() {
    return this.code === 'not_registered'
  }

  get isDeactivated() {
    return this.code === 'deactivated'
  }
}

interface ErrorBody {
  detail?: { code?: string; message?: string } | string
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = 'http_error'
  let message = `Xatolik (${response.status})`

  try {
    const body = (await response.json()) as ErrorBody
    if (typeof body.detail === 'string') {
      message = body.detail
    } else if (body.detail) {
      code = body.detail.code ?? code
      message = body.detail.message ?? message
    }
  } catch {
    // Javob JSON bo'lmasa standart xabar qoladi
  }

  return new ApiError(response.status, code, message)
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export function createApi(initData: string) {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${BASE_URL}/api${path}`, {
      ...init,
      headers: {
        Authorization: `tma ${initData}`,
        ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...init?.headers,
      },
    })

    if (!response.ok) {
      throw await toApiError(response)
    }
    if (response.status === 204) {
      return undefined as T
    }
    return (await response.json()) as T
  }

  return {
    getMe: () => request<User>('/me'),

    getDistricts: () => request<District[]>('/districts'),

    listReports: (params: {
      day?: string
      user_id?: number
      status?: ReportStatus
      page?: number
      per_page?: number
    }) => request<Page<Report>>(`/reports${query(params)}`),

    getReport: (id: number) => request<Report>(`/reports/${id}`),

    approveReport: (id: number) =>
      request<Report>(`/reports/${id}/approve`, { method: 'POST' }),

    rejectReport: (id: number) =>
      request<Report>(`/reports/${id}/reject`, { method: 'POST' }),

    listEmployees: (params: {
      page?: number
      per_page?: number
      only_active?: boolean
    }) =>
      request<Page<User>>(
        `/employees${query({
          page: params.page,
          per_page: params.per_page,
          only_active: params.only_active ? 'true' : undefined,
        })}`,
      ),

    getEmployee: (id: number) => request<User>(`/employees/${id}`),
  }
}

export type Api = ReturnType<typeof createApi>
