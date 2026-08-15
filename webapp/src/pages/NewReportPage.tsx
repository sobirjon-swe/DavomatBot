import { AlertCircle, Camera, Check, Loader2, MapPin, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ErrorScreen, LoadingScreen } from '@/components/StatusScreen'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/input'
import { MAX_PHOTOS, MIN_PHOTOS, type District, type Report } from '@/lib/api'
import {
  canOpenLocationSettings,
  getCurrentLocation,
  LocationError,
  openLocationSettings,
  type Coordinates,
} from '@/lib/location'
import { useApi, useColleagues, useCreateReport, useDistricts, useMe } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { hasMainButton, useMainButton } from '@/telegram/mainButton'

const TYPES: { value: Report['report_type']; label: string }[] = [
  { value: 'laboratory', label: 'Laboratoriya' },
  { value: 'visual', label: "Visual ko'rik" },
  { value: 'instrumental', label: "Instrumental ko'rik" },
]

interface PhotoItem {
  key: string
  previewUrl: string
  fileId?: string
  status: 'uploading' | 'done' | 'error'
}

function Section({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string
  children: ReactNode
}) {
  return (
    <section className="space-y-2">
      <div>
        <h2 className="text-sm font-medium">{title}</h2>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </section>
  )
}

export function NewReportPage() {
  const navigate = useNavigate()
  const api = useApi()
  const me = useMe()
  const colleagues = useColleagues()
  const allDistricts = useDistricts()
  const createReport = useCreateReport()

  const [type, setType] = useState<Report['report_type'] | null>(null)
  const [districtId, setDistrictId] = useState<number | null>(null)
  const [useAllDistricts, setUseAllDistricts] = useState(false)
  const [customer, setCustomer] = useState('')
  const [plots, setPlots] = useState('')
  const [partnerIds, setPartnerIds] = useState<number[]>([])
  const [photos, setPhotos] = useState<PhotoItem[]>([])
  const [location, setLocation] = useState<Coordinates | null>(null)
  const [locationError, setLocationError] = useState<LocationError | null>(null)
  const [locating, setLocating] = useState(false)

  const fileInput = useRef<HTMLInputElement>(null)

  // Ko'rish uchun yaratilgan blob URL lar oqib ketmasin
  const photosRef = useRef(photos)
  photosRef.current = photos
  // photos.length ning sinxron (render tsiklidan mustaqil) nusxasi —
  // addFiles ichida MAX_PHOTOS chegarasini to'g'ri hisoblash uchun kerak.
  const photosCountRef = useRef(0)
  useEffect(
    () => () => {
      for (const photo of photosRef.current) URL.revokeObjectURL(photo.previewUrl)
    },
    [],
  )

  const myDistricts: District[] = me.data?.districts ?? []
  const districts =
    useAllDistricts || myDistricts.length === 0 ? (allDistricts.data ?? []) : myDistricts

  const uploadedIds = photos
    .filter((p) => p.fileId !== undefined)
    .map((p) => p.fileId as string)
  const isUploading = photos.some((p) => p.status === 'uploading')

  const missing = useMemo(() => {
    const items: string[] = []
    if (!type) items.push('turi')
    if (!districtId) items.push('hudud')
    if (!customer.trim()) items.push('buyurtmachi')
    if (!location) items.push('joylashuv')
    if (uploadedIds.length < MIN_PHOTOS) {
      items.push(`yana ${MIN_PHOTOS - uploadedIds.length} ta rasm`)
    }
    return items
  }, [type, districtId, customer, location, uploadedIds.length])

  const canSubmit = missing.length === 0 && !isUploading && !createReport.isPending

  const detectLocation = useCallback(async () => {
    setLocating(true)
    setLocationError(null)
    try {
      setLocation(await getCurrentLocation())
    } catch (error) {
      setLocationError(
        error instanceof LocationError
          ? error
          : new LocationError('unavailable', "Joylashuvni aniqlab bo'lmadi"),
      )
    } finally {
      setLocating(false)
    }
  }, [])

  async function addFiles(files: FileList | null) {
    if (!files) return

    // `room` photosCountRef dan hisoblanadi, `photos.length` state dan emas —
    // state React render tsikliga bog'liq, shuning uchun addFiles ketma-ket
    // (render orasida) chaqirilsa ikkalasi ham eski uzunlikni ko'rib,
    // MAX_PHOTOS dan ko'p rasm qo'shilib ketishi mumkin edi. Ref esa
    // darhol, sinxron yangilanadi.
    const room = MAX_PHOTOS - photosCountRef.current
    const selected = Array.from(files).slice(0, Math.max(room, 0))
    photosCountRef.current += selected.length

    for (const file of selected) {
      const key = `${file.name}-${file.size}-${file.lastModified}-${Math.random()}`
      setPhotos((prev) => [
        ...prev,
        { key, previewUrl: URL.createObjectURL(file), status: 'uploading' },
      ])

      try {
        const { file_id } = await api.uploadPhoto(file)
        setPhotos((prev) =>
          prev.map((p) => (p.key === key ? { ...p, fileId: file_id, status: 'done' } : p)),
        )
      } catch {
        setPhotos((prev) => prev.map((p) => (p.key === key ? { ...p, status: 'error' } : p)))
      }
    }

    // Bir xil faylni qayta tanlash mumkin bo'lsin
    if (fileInput.current) fileInput.current.value = ''
  }

  function removePhoto(key: string) {
    setPhotos((prev) => {
      const target = prev.find((p) => p.key === key)
      if (target) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((p) => p.key !== key)
    })
    photosCountRef.current = Math.max(0, photosCountRef.current - 1)
  }

  function togglePartner(id: number) {
    setPartnerIds((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]))
  }

  const submit = useCallback(() => {
    if (!canSubmit || !type || !districtId || !location) return

    createReport.mutate(
      {
        report_type: type,
        district_id: districtId,
        customer_name: customer.trim(),
        lat: location.lat,
        lon: location.lon,
        plots_count: type === 'laboratory' && plots ? Number(plots) : null,
        partner_ids: partnerIds,
        photo_file_ids: uploadedIds,
      },
      {
        onSuccess: (report) => navigate(`/reports/${report.id}`, { replace: true }),
      },
    )
  }, [
    canSubmit,
    type,
    districtId,
    location,
    customer,
    plots,
    partnerIds,
    uploadedIds,
    createReport,
    navigate,
  ])

  useMainButton({
    text: createReport.isPending ? 'Yuborilmoqda...' : 'Yuborish',
    isEnabled: canSubmit,
    isLoaderVisible: createReport.isPending,
    onClick: submit,
  })

  if (me.isLoading) return <LoadingScreen />
  if (me.error) return <ErrorScreen error={me.error} />

  return (
    <div className="space-y-6 p-4 pb-8">
      <h1 className="text-lg font-semibold">Yangi hisobot</h1>

      <Section title="Ma'lumot turi">
        <div className="flex flex-col gap-2">
          {TYPES.map(({ value, label }) => (
            <Button
              key={value}
              variant={type === value ? 'default' : 'secondary'}
              className="justify-start"
              onClick={() => setType(value)}
            >
              {type === value && <Check />}
              {label}
            </Button>
          ))}
        </div>
      </Section>

      <Section
        title="Hudud"
        hint={
          myDistricts.length > 0 && !useAllDistricts
            ? 'Sizga biriktirilgan hududlar'
            : undefined
        }
      >
        <Select
          value={districtId ?? ''}
          onChange={(event) => setDistrictId(Number(event.target.value) || null)}
        >
          <option value="">Tanlang...</option>
          {districts.map((district) => (
            <option key={district.id} value={district.id}>
              {district.name_uz}
            </option>
          ))}
        </Select>

        {myDistricts.length > 0 && !useAllDistricts && (
          <Button
            variant="link"
            size="sm"
            className="h-auto p-0"
            onClick={() => {
              setUseAllDistricts(true)
              setDistrictId(null)
            }}
          >
            Boshqa hudud kerakmi?
          </Button>
        )}
      </Section>

      <Section title="Buyurtmachi">
        <Input
          value={customer}
          onChange={(event) => setCustomer(event.target.value)}
          placeholder="Tashkilot yoki shaxs nomi"
          maxLength={500}
        />
      </Section>

      {type === 'laboratory' && (
        <Section title="Uchastkalar soni" hint="Ixtiyoriy">
          <Input
            value={plots}
            onChange={(event) => setPlots(event.target.value.replace(/\D/g, ''))}
            inputMode="numeric"
            placeholder="0"
          />
        </Section>
      )}

      <Section title="Sheriklar" hint="Ixtiyoriy, bir nechtasini tanlash mumkin">
        {colleagues.isLoading ? (
          <p className="text-sm text-muted-foreground">Yuklanmoqda...</p>
        ) : (colleagues.data?.length ?? 0) === 0 ? (
          <p className="text-sm text-muted-foreground">Boshqa hodim yo'q</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {colleagues.data?.map((partner) => (
              <Button
                key={partner.id}
                size="sm"
                variant={partnerIds.includes(partner.id) ? 'default' : 'secondary'}
                onClick={() => togglePartner(partner.id)}
              >
                {partner.full_name}
              </Button>
            ))}
          </div>
        )}
      </Section>

      <Section title="Joylashuv">
        {location ? (
          <div className="flex items-center gap-2 rounded-md border border-border bg-card p-3">
            <MapPin className="size-4 shrink-0 text-success" />
            <span className="flex-1 text-sm">
              {location.lat.toFixed(5)}, {location.lon.toFixed(5)}
              {location.accuracy !== undefined && (
                <span className="text-muted-foreground">
                  {' '}
                  &middot; ±{Math.round(location.accuracy)} m
                </span>
              )}
            </span>
            <Button size="sm" variant="ghost" onClick={detectLocation} disabled={locating}>
              Yangilash
            </Button>
          </div>
        ) : (
          <Button
            variant="outline"
            className="w-full"
            onClick={detectLocation}
            disabled={locating}
          >
            {locating ? <Loader2 className="animate-spin" /> : <MapPin />}
            {locating ? 'Aniqlanmoqda...' : 'Joylashuvni aniqlash'}
          </Button>
        )}

        {locationError && (
          <div className="space-y-2 rounded-md border border-destructive/40 p-3">
            <p className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="size-4 shrink-0" />
              {locationError.message}
            </p>
            {locationError.code === 'denied' && canOpenLocationSettings() && (
              <Button size="sm" variant="secondary" onClick={openLocationSettings}>
                Sozlamalarni ochish
              </Button>
            )}
            <p className="text-xs text-muted-foreground">
              Ishlamasa hisobotni bot orqali yuboring — chatdagi "Joylashuvni yuborish"
              tugmasi barcha qurilmalarda ishlaydi.
            </p>
          </div>
        )}
      </Section>

      <Section
        title="Rasmlar"
        hint={`${uploadedIds.length}/${MIN_PHOTOS} kerak, ko'pi bilan ${MAX_PHOTOS} ta`}
      >
        <div className="grid grid-cols-3 gap-2">
          {photos.map((photo) => (
            <div
              key={photo.key}
              className="relative aspect-square overflow-hidden rounded-md border border-border"
            >
              <img
                src={photo.previewUrl}
                alt=""
                className={cn('size-full object-cover', photo.status !== 'done' && 'opacity-50')}
              />
              {photo.status === 'uploading' && (
                <Loader2 className="absolute inset-0 m-auto size-5 animate-spin" />
              )}
              {photo.status === 'error' && (
                <AlertCircle className="absolute inset-0 m-auto size-5 text-destructive" />
              )}
              <button
                type="button"
                onClick={() => removePhoto(photo.key)}
                className="absolute right-1 top-1 rounded-full bg-background/80 p-1"
                aria-label="Rasmni o'chirish"
              >
                <X className="size-3" />
              </button>
            </div>
          ))}

          {photos.length < MAX_PHOTOS && (
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              className="flex aspect-square items-center justify-center rounded-md border border-dashed border-border text-muted-foreground"
              aria-label="Rasm qo'shish"
            >
              <Camera className="size-6" />
            </button>
          )}
        </div>

        {/*
          `capture` ataylab qo'yilmagan: u kamerani majburlab, galereyadan
          tanlashni va `multiple` ni ishlamay qo'yadi. Botdagi oqim ham
          galereyaga ruxsat berardi — xatti-harakat bir xil qoladi.
        */}
        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(event) => void addFiles(event.target.files)}
        />

        {photos.some((p) => p.status === 'error') && (
          <p className="text-xs text-destructive">
            Ba'zi rasmlar yuklanmadi — ularni o'chirib qayta urinib ko'ring.
          </p>
        )}
      </Section>

      {createReport.error && (
        <p className="text-sm text-destructive">
          {createReport.error instanceof Error
            ? createReport.error.message
            : 'Yuborishda xatolik'}
        </p>
      )}

      {missing.length > 0 && (
        <p className="text-sm text-muted-foreground">
          Yuborish uchun kerak: {missing.join(', ')}.
        </p>
      )}

      {/* Telegram MainButton yo'q bo'lsa (brauzer, eski mijoz) — oddiy tugma */}
      {!hasMainButton() && (
        <Button className="w-full" disabled={!canSubmit} onClick={submit}>
          {createReport.isPending ? <Loader2 className="animate-spin" /> : null}
          Yuborish
        </Button>
      )}
    </div>
  )
}
