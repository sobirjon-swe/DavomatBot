import { backButton } from '@telegram-apps/sdk-react'
import { ClipboardList, Users } from 'lucide-react'
import { useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import type { User } from '@/lib/api'
import { cn } from '@/lib/utils'

const TABS = [
  { to: '/', label: 'Hisobotlar', icon: ClipboardList, adminOnly: false },
  { to: '/employees', label: 'Hodimlar', icon: Users, adminOnly: true },
] as const

function isRootRoute(pathname: string): boolean {
  return TABS.some((tab) => tab.to === pathname)
}

export function AppShell({ me }: { me: User }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const isAdmin = me.role === 'admin' || me.role === 'superadmin'
  const tabs = TABS.filter((tab) => !tab.adminOnly || isAdmin)

  // Telegram ning tizim "orqaga" tugmasi faqat ichki sahifalarda ko'rinadi.
  useEffect(() => {
    if (!backButton.isMounted()) return
    if (isRootRoute(pathname)) {
      backButton.hide()
    } else {
      backButton.show()
    }
  }, [pathname])

  useEffect(() => {
    if (!backButton.onClick.isAvailable()) return
    return backButton.onClick(() => navigate(-1))
  }, [navigate])

  return (
    <div className="flex min-h-dvh flex-col">
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
