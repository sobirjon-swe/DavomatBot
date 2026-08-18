import { backButton } from '@telegram-apps/sdk-react'
import {
  ClipboardCheck,
  ClipboardList,
  ListChecks,
  PlusCircle,
  Settings,
  Users,
} from 'lucide-react'
import { useEffect } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import type { User } from '@/lib/api'
import { cn } from '@/lib/utils'

// Botda hodim va admin menyulari butunlay alohida (hodim hisobot topshiradi,
// admin uni ko'rib chiqadi — admin hech qachon hisobot topshirmaydi). Shu
// tufayli bitta ro'yxatni "adminOnly" bayrog'i bilan filtrlash o'rniga har
// bir rol uchun alohida, to'liq tab ro'yxati beriladi — aks holda "hamma
// uchun ochiq" tugma (masalan "Yangi") admin panelga aralashib qolishi
// mumkin edi.
const EMPLOYEE_TABS = [
  { to: '/', label: 'Hisobotlar', icon: ClipboardList },
  { to: '/new', label: 'Yangi', icon: PlusCircle },
] as const

const ADMIN_TABS = [
  { to: '/', label: 'Hisobotlar', icon: ListChecks },
  { to: '/attendance', label: 'Davomat', icon: ClipboardCheck },
  { to: '/employees', label: 'Hodimlar', icon: Users },
] as const

export function AppShell({ me }: { me: User }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const isAdmin = me.role === 'admin' || me.role === 'superadmin'
  const tabs = isAdmin ? ADMIN_TABS : EMPLOYEE_TABS

  // Telegram ning tizim "orqaga" tugmasi faqat ichki sahifalarda ko'rinadi.
  useEffect(() => {
    if (!backButton.isMounted()) return
    if (tabs.some((tab) => tab.to === pathname)) {
      backButton.hide()
    } else {
      backButton.show()
    }
  }, [pathname, tabs])

  useEffect(() => {
    if (!backButton.onClick.isAvailable()) return
    return backButton.onClick(() => navigate(-1))
  }, [navigate])

  return (
    <div className="flex min-h-dvh flex-col">
      {isAdmin && (
        <header className="flex justify-end px-4 pt-3">
          <Link
            to="/settings"
            className={cn(
              'flex size-9 items-center justify-center rounded-full',
              pathname === '/settings' ? 'text-primary' : 'text-muted-foreground',
            )}
            aria-label="Sozlamalar"
          >
            <Settings className="size-5" />
          </Link>
        </header>
      )}

      <main className="flex-1 pb-20">
        <Outlet />
      </main>

      {tabs.length > 1 && (
        <nav className="fixed inset-x-0 bottom-0 border-t border-border bg-card pb-[var(--tg-viewport-safe-area-inset-bottom,0px)]">
          <div className="mx-auto flex max-w-md">
            {tabs.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex flex-1 flex-col items-center gap-1 py-2 text-xs transition-colors',
                    isActive ? 'text-primary' : 'text-muted-foreground',
                  )
                }
              >
                <Icon className="size-5" />
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </div>
  )
}
