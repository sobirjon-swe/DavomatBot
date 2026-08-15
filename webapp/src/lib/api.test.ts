import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, createApi } from './api'

const INIT_DATA = 'auth_date=1&user=%7B%22id%22%3A1%7D&hash=abc'

function mockFetch(response: Record<string, unknown>) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({}),
    ...response,
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

describe('so‘rov yuborish', () => {
  it('initData ni Authorization sarlavhasida yuboradi', async () => {
    const fetchMock = mockFetch({ json: async () => ({ id: 1 }) })

    await createApi(INIT_DATA).getMe()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/me')
    expect(init.headers.Authorization).toBe(`tma ${INIT_DATA}`)
  })

  it('JSON tanasi uchun Content-Type qo‘yadi', async () => {
    const fetchMock = mockFetch({ status: 201, json: async () => ({ id: 5 }) })

    await createApi(INIT_DATA).createReport({
      report_type: 'visual',
      district_id: 1,
      customer_name: 'Mijoz',
      lat: 41,
      lon: 69,
      partner_ids: [],
      photo_file_ids: ['a', 'b', 'c'],
    })

    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers['Content-Type']).toBe('application/json')
  })

  it('FormData uchun Content-Type QO‘YMAYDI', async () => {
    // Brauzer uni boundary bilan birga o‘zi yozishi kerak; qo‘lda
    // qo‘yilsa server multipart ni ajrata olmaydi.
    const fetchMock = mockFetch({ status: 201, json: async () => ({ file_id: 'f1' }) })

    await createApi(INIT_DATA).uploadPhoto(
      new File(['x'], 'a.jpg', { type: 'image/jpeg' }),
    )

    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers['Content-Type']).toBeUndefined()
    expect(init.body).toBeInstanceOf(FormData)
  })
})

describe('query parametrlari', () => {
  it('faqat berilgan qiymatlarni qo‘shadi', async () => {
    const fetchMock = mockFetch({ json: async () => ({ items: [] }) })

    await createApi(INIT_DATA).listReports({ page: 2, status: 'pending' })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/reports?page=2&status=pending')
  })

  it('bo‘sh so‘rovda savol belgisi qo‘shilmaydi', async () => {
    const fetchMock = mockFetch({ json: async () => ({ items: [] }) })

    await createApi(INIT_DATA).listReports({})

    expect(fetchMock.mock.calls[0][0]).toBe('/api/reports')
  })
})

describe('xatolar', () => {
  it('server bergan code va message ni o‘qiydi', async () => {
    mockFetch({
      ok: false,
      status: 403,
      json: async () => ({
        detail: { code: 'not_registered', message: 'Avval botda ro‘yxatdan o‘ting' },
      }),
    })

    const error = await createApi(INIT_DATA)
      .getMe()
      .catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('not_registered')
    expect((error as ApiError).isNotRegistered).toBe(true)
  })

  it('faolsizlantirilgan hisobni ajratadi', async () => {
    mockFetch({
      ok: false,
      status: 403,
      json: async () => ({ detail: { code: 'deactivated', message: 'Faolsiz' } }),
    })

    const error = (await createApi(INIT_DATA)
      .getMe()
      .catch((e: unknown) => e)) as ApiError

    expect(error.isDeactivated).toBe(true)
    expect(error.isNotRegistered).toBe(false)
  })

  it('detail satr bo‘lsa ham ishlaydi', async () => {
    // FastAPI ba'zi ichki xatolarda oddiy satr qaytaradi
    mockFetch({ ok: false, status: 422, json: async () => ({ detail: 'Noto‘g‘ri' }) })

    const error = (await createApi(INIT_DATA)
      .getMe()
      .catch((e: unknown) => e)) as ApiError

    expect(error.message).toBe('Noto‘g‘ri')
  })

  it('JSON bo‘lmagan javobda ham yiqilmaydi', async () => {
    mockFetch({
      ok: false,
      status: 502,
      json: async () => {
        throw new Error('not json')
      },
    })

    const error = (await createApi(INIT_DATA)
      .getMe()
      .catch((e: unknown) => e)) as ApiError

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(502)
  })
})
