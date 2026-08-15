import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const locationManager = {
  mount: Object.assign(vi.fn(), { isAvailable: vi.fn(() => false) }),
  isMounted: vi.fn(() => false),
  requestLocation: Object.assign(vi.fn(), { isAvailable: vi.fn(() => true) }),
  openSettings: Object.assign(vi.fn(), { isAvailable: vi.fn(() => false) }),
  isAccessRequested: vi.fn(() => false),
  isAccessGranted: vi.fn(() => true),
}

vi.mock('@telegram-apps/sdk-react', () => ({
  get locationManager() {
    return locationManager
  },
}))

const { getCurrentLocation, LocationError } = await import('./location')

function position(lat: number, lon: number, accuracy: number) {
  return { coords: { latitude: lat, longitude: lon, accuracy } } as GeolocationPosition
}

function mockGeolocation(impl: Partial<Geolocation>) {
  vi.stubGlobal('navigator', { geolocation: impl })
}

beforeEach(() => {
  locationManager.mount.isAvailable.mockReturnValue(false)
  locationManager.isMounted.mockReturnValue(false)
  locationManager.requestLocation.isAvailable.mockReturnValue(true)
  locationManager.isAccessRequested.mockReturnValue(false)
  locationManager.isAccessGranted.mockReturnValue(true)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Telegram LocationManager', () => {
  it('latitude/longitude shaklini o‘qiydi', async () => {
    locationManager.mount.isAvailable.mockReturnValue(true)
    locationManager.isMounted.mockReturnValue(true)
    locationManager.requestLocation.mockResolvedValue({
      latitude: 41.31,
      longitude: 69.24,
      horizontal_accuracy: 12,
    })

    expect(await getCurrentLocation()).toEqual({ lat: 41.31, lon: 69.24, accuracy: 12 })
  })

  it('lat/lon qisqa shaklini ham o‘qiydi', async () => {
    // SDK bu qiymatni tiplamaydi va mijoz versiyasiga qarab nom farq qiladi
    locationManager.mount.isAvailable.mockReturnValue(true)
    locationManager.isMounted.mockReturnValue(true)
    locationManager.requestLocation.mockResolvedValue({ lat: 41.5, lon: 69.5 })

    expect(await getCurrentLocation()).toEqual({
      lat: 41.5,
      lon: 69.5,
      accuracy: undefined,
    })
  })

  it('mount qilinmagan bo‘lsa avval mount qiladi', async () => {
    locationManager.mount.isAvailable.mockReturnValue(true)
    locationManager.isMounted.mockReturnValue(false)
    locationManager.mount.mockResolvedValue(undefined)
    locationManager.requestLocation.mockResolvedValue({ latitude: 41, longitude: 69 })

    await getCurrentLocation()

    expect(locationManager.mount).toHaveBeenCalled()
  })

  it('Telegram xato bersa brauzerga o‘tadi', async () => {
    locationManager.mount.isAvailable.mockReturnValue(true)
    locationManager.isMounted.mockReturnValue(true)
    locationManager.requestLocation.mockRejectedValue(new Error('ruxsat yo‘q'))
    mockGeolocation({
      getCurrentPosition: (success) => success(position(42, 70, 5)),
    })

    expect(await getCurrentLocation()).toEqual({ lat: 42, lon: 70, accuracy: 5 })
  })

  it('ruxsat aniq rad etilsa brauzerga o‘tmay "denied" beradi', async () => {
    locationManager.mount.isAvailable.mockReturnValue(true)
    locationManager.isMounted.mockReturnValue(true)
    locationManager.requestLocation.mockRejectedValue(new Error('access denied'))
    locationManager.isAccessRequested.mockReturnValue(true)
    locationManager.isAccessGranted.mockReturnValue(false)

    const failure = (await getCurrentLocation().catch((e: unknown) => e)) as InstanceType<
      typeof LocationError
    >
    expect(failure).toBeInstanceOf(LocationError)
    expect(failure.code).toBe('denied')
  })

  it('tushunarsiz javob kelsa brauzerga o‘tadi', async () => {
    locationManager.mount.isAvailable.mockReturnValue(true)
    locationManager.isMounted.mockReturnValue(true)
    locationManager.requestLocation.mockResolvedValue({ nimadir: 'boshqa' })
    mockGeolocation({
      getCurrentPosition: (success) => success(position(42, 70, 5)),
    })

    expect((await getCurrentLocation()).lat).toBe(42)
  })
})

describe('brauzer geolokatsiyasi', () => {
  it('koordinatalarni qaytaradi', async () => {
    mockGeolocation({
      getCurrentPosition: (success) => success(position(41.2, 69.1, 8)),
    })

    expect(await getCurrentLocation()).toEqual({ lat: 41.2, lon: 69.1, accuracy: 8 })
  })

  it('ruxsat rad etilsa "denied" kodini beradi', async () => {
    mockGeolocation({
      getCurrentPosition: (_success, error) =>
        error?.({ code: 1, PERMISSION_DENIED: 1, TIMEOUT: 3 } as GeolocationPositionError),
    })

    const failure = (await getCurrentLocation().catch((e: unknown) => e)) as InstanceType<typeof LocationError>
    expect(failure).toBeInstanceOf(LocationError)
    expect(failure.code).toBe('denied')
  })

  it('vaqt tugasa "timeout" kodini beradi', async () => {
    mockGeolocation({
      getCurrentPosition: (_success, error) =>
        error?.({ code: 3, PERMISSION_DENIED: 1, TIMEOUT: 3 } as GeolocationPositionError),
    })

    const failure = (await getCurrentLocation().catch((e: unknown) => e)) as InstanceType<typeof LocationError>
    expect(failure.code).toBe('timeout')
  })

  it('geolokatsiya umuman bo‘lmasa "unavailable"', async () => {
    vi.stubGlobal('navigator', {})

    const failure = (await getCurrentLocation().catch((e: unknown) => e)) as InstanceType<typeof LocationError>
    expect(failure.code).toBe('unavailable')
  })
})
