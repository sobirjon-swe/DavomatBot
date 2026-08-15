import { describe, expect, it } from 'vitest'

import { cn, formatDateTime, formatTime, mapsUrl, toApiDate } from './utils'

describe('cn', () => {
  it('shartli sinflarni qo‘shadi', () => {
    expect(cn('a', false && 'b', 'c')).toBe('a c')
  })

  it('Tailwind ziddiyatida oxirgisi yutadi', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
  })
})

describe('vaqt formatlash', () => {
  // Toshkent = UTC+5
  it('UTC vaqtni Toshkent mintaqasida ko‘rsatadi', () => {
    expect(formatDateTime('2026-06-05T06:30:00+00:00')).toBe('05.06.2026 11:30')
  })

  it('sana chegarasidan o‘tishni to‘g‘ri hisoblaydi', () => {
    // UTC 4-iyun 20:00 = Toshkent 5-iyun 01:00
    expect(formatDateTime('2026-06-04T20:00:00+00:00')).toBe('05.06.2026 01:00')
  })

  it('faqat vaqtni bera oladi', () => {
    expect(formatTime('2026-06-05T06:30:00+00:00')).toBe('11:30')
  })
})

describe('toApiDate', () => {
  it('YYYY-MM-DD beradi', () => {
    expect(toApiDate(new Date('2026-06-05T06:30:00Z'))).toBe('2026-06-05')
  })

  it('kunni Toshkent bo‘yicha hisoblaydi, UTC bo‘yicha emas', () => {
    // UTC da bu hali 4-iyun kechqurun, Toshkentda esa 5-iyun tongi
    expect(toApiDate(new Date('2026-06-04T20:00:00Z'))).toBe('2026-06-05')
  })
})

describe('mapsUrl', () => {
  it('koordinatalardan havola yasaydi', () => {
    expect(mapsUrl(41.31, 69.24)).toBe('https://maps.google.com/?q=41.31,69.24')
  })
})
