import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LocationError } from '@/lib/location'

const navigate = vi.fn()
vi.mock('react-router-dom', () => ({
  useNavigate: () => navigate,
}))

// MainButton yo'q deb ko'rsatamiz — shunda sahifa ichidagi tugma render
// bo'ladi va uni bosib tekshirish mumkin.
vi.mock('@/telegram/mainButton', () => ({
  hasMainButton: () => false,
  useMainButton: () => {},
}))

const getCurrentLocation = vi.fn()
vi.mock('@/lib/location', async () => {
  const actual = await vi.importActual<typeof import('@/lib/location')>('@/lib/location')
  return {
    ...actual,
    getCurrentLocation: () => getCurrentLocation(),
    canOpenLocationSettings: () => false,
    openLocationSettings: () => {},
  }
})

const uploadPhoto = vi.fn()
const createReportMutate = vi.fn()

vi.mock('@/lib/queries', () => ({
  useApi: () => ({ uploadPhoto }),
  useMe: () => ({
    data: {
      id: 1,
      full_name: 'Ali Valiyev',
      position: 'Muhandis',
      role: 'employee',
      districts: [{ id: 7, name_uz: 'Qibray tumani', name_ru: 'Кибрайский район' }],
    },
    isLoading: false,
    error: null,
  }),
  useColleagues: () => ({
    data: [{ id: 2, full_name: 'Vali Aliyev', position: 'Texnik' }],
    isLoading: false,
  }),
  useDistricts: () => ({ data: [] }),
  useCreateReport: () => ({
    mutate: createReportMutate,
    isPending: false,
    error: null,
  }),
}))

const { NewReportPage } = await import('./NewReportPage')

function photoFile(name: string) {
  return new File(['x'], name, { type: 'image/jpeg' })
}

function fileInput() {
  return document.querySelector('input[type="file"]') as HTMLInputElement
}

async function fillEverything(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Laboratoriya' }))
  await user.selectOptions(screen.getByRole('combobox'), '7')
  await user.type(screen.getByPlaceholderText('Tashkilot yoki shaxs nomi'), 'Mijoz OOO')
  await user.click(screen.getByRole('button', { name: /Joylashuvni aniqlash/ }))
  await user.upload(fileInput(), [
    photoFile('a.jpg'),
    photoFile('b.jpg'),
    photoFile('c.jpg'),
  ])
}

beforeEach(() => {
  // mockReset shart: config dagi restoreMocks oddiy vi.fn() ning chaqiruvlar
  // tarixini tozalamaydi va hisob testdan testga o'tib ketadi.
  navigate.mockReset()
  createReportMutate.mockReset()
  uploadPhoto.mockReset()
  getCurrentLocation.mockReset()

  getCurrentLocation.mockResolvedValue({ lat: 41.31, lon: 69.24, accuracy: 10 })
  uploadPhoto.mockImplementation(async (file: File) => ({ file_id: `id-${file.name}` }))
})

describe('yetishmayotgan maydonlar', () => {
  it('boshida hammasi ko‘rsatiladi', () => {
    render(<NewReportPage />)

    const hint = screen.getByText(/Yuborish uchun kerak/)
    expect(hint).toHaveTextContent('turi')
    expect(hint).toHaveTextContent('hudud')
    expect(hint).toHaveTextContent('buyurtmachi')
    expect(hint).toHaveTextContent('joylashuv')
    expect(hint).toHaveTextContent('yana 3 ta rasm')
  })

  it('yetarli rasm bo‘lmasa nechta kerakligini aytadi', async () => {
    const user = userEvent.setup()
    render(<NewReportPage />)

    await user.upload(fileInput(), [photoFile('a.jpg')])

    await waitFor(() =>
      expect(screen.getByText(/Yuborish uchun kerak/)).toHaveTextContent('yana 2 ta rasm'),
    )
  })
})

describe('shartli maydonlar', () => {
  it('uchastkalar maydoni faqat laboratoriya uchun chiqadi', async () => {
    const user = userEvent.setup()
    render(<NewReportPage />)

    expect(screen.queryByText('Uchastkalar soni')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Laboratoriya' }))
    expect(screen.getByText('Uchastkalar soni')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Visual/ }))
    expect(screen.queryByText('Uchastkalar soni')).not.toBeInTheDocument()
  })

  it('hodimga biriktirilgan tumanlar ko‘rsatiladi', () => {
    render(<NewReportPage />)

    expect(screen.getByRole('option', { name: 'Qibray tumani' })).toBeInTheDocument()
  })
})

describe('yuborish', () => {
  it('hamma maydon to‘lgach so‘rov yuboriladi', async () => {
    const user = userEvent.setup()
    render(<NewReportPage />)

    await fillEverything(user)
    await waitFor(() => expect(uploadPhoto).toHaveBeenCalledTimes(3))

    const submit = screen.getByRole('button', { name: 'Yuborish' })
    await waitFor(() => expect(submit).toBeEnabled())
    await user.click(submit)

    expect(createReportMutate).toHaveBeenCalledTimes(1)
    expect(createReportMutate.mock.calls[0][0]).toEqual({
      report_type: 'laboratory',
      district_id: 7,
      customer_name: 'Mijoz OOO',
      lat: 41.31,
      lon: 69.24,
      plots_count: null,
      partner_ids: [],
      photo_file_ids: ['id-a.jpg', 'id-b.jpg', 'id-c.jpg'],
    })
  })

  it('to‘liq bo‘lmagan formada tugma o‘chiq', () => {
    render(<NewReportPage />)

    expect(screen.getByRole('button', { name: 'Yuborish' })).toBeDisabled()
  })

  it('tanlangan sherik so‘rovga qo‘shiladi', async () => {
    const user = userEvent.setup()
    render(<NewReportPage />)

    await fillEverything(user)
    await user.click(screen.getByRole('button', { name: 'Vali Aliyev' }))
    await waitFor(() => expect(uploadPhoto).toHaveBeenCalledTimes(3))

    const submit = screen.getByRole('button', { name: 'Yuborish' })
    await waitFor(() => expect(submit).toBeEnabled())
    await user.click(submit)

    expect(createReportMutate.mock.calls[0][0].partner_ids).toEqual([2])
  })
})

describe('rasmlar', () => {
  it('yuklanmagan rasm hisobga olinmaydi', async () => {
    const user = userEvent.setup()
    uploadPhoto.mockRejectedValue(new Error('tarmoq'))
    render(<NewReportPage />)

    await user.upload(fileInput(), [photoFile('a.jpg')])

    await waitFor(() =>
      expect(screen.getByText(/Ba'zi rasmlar yuklanmadi/)).toBeInTheDocument(),
    )
    // Yuklanmagan rasm "yana 3 ta kerak" hisobini o‘zgartirmaydi
    expect(screen.getByText(/Yuborish uchun kerak/)).toHaveTextContent('yana 3 ta rasm')
  })

  it('rasmni o‘chirish mumkin', async () => {
    const user = userEvent.setup()
    render(<NewReportPage />)

    await user.upload(fileInput(), [photoFile('a.jpg')])
    await waitFor(() => expect(uploadPhoto).toHaveBeenCalled())

    await user.click(screen.getByRole('button', { name: "Rasmni o'chirish" }))

    expect(
      screen.queryByRole('button', { name: "Rasmni o'chirish" }),
    ).not.toBeInTheDocument()
  })
})

describe('joylashuv', () => {
  it('aniqlangach koordinatalar ko‘rinadi', async () => {
    const user = userEvent.setup()
    render(<NewReportPage />)

    await user.click(screen.getByRole('button', { name: /Joylashuvni aniqlash/ }))

    await waitFor(() =>
      expect(screen.getByText(/41\.31000, 69\.24000/)).toBeInTheDocument(),
    )
  })

  it('ruxsat berilmasa bot orqali yuborish taklif qilinadi', async () => {
    const user = userEvent.setup()
    getCurrentLocation.mockRejectedValue(new LocationError('denied', 'Ruxsat berilmadi'))
    render(<NewReportPage />)

    await user.click(screen.getByRole('button', { name: /Joylashuvni aniqlash/ }))

    await waitFor(() => expect(screen.getByText('Ruxsat berilmadi')).toBeInTheDocument())
    expect(screen.getByText(/hisobotni bot orqali yuboring/)).toBeInTheDocument()
  })
})
