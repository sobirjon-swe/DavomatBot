import { useState } from 'react'

import { EmptyScreen, ErrorScreen } from '@/components/StatusScreen'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { Role, User } from '@/lib/api'
import { useEmployees } from '@/lib/queries'

const ROLE_LABEL: Record<Role, string> = {
  superadmin: 'Super admin',
  admin: 'Admin',
  employee: 'Hodim',
}

function EmployeeRow({ user }: { user: User }) {
  return (
    <div className="border-b border-border px-4 py-3 last:border-0">
      <div className="flex items-center gap-2">
        <p className="min-w-0 flex-1 truncate font-medium">{user.full_name}</p>
        {user.role !== 'employee' && (
          <Badge variant="outline">{ROLE_LABEL[user.role]}</Badge>
        )}
        {!user.is_active && <Badge variant="destructive">Faolsiz</Badge>}
        {!user.is_linked && <Badge variant="secondary">Kirmagan</Badge>}
      </div>
      <p className="truncate text-sm text-muted-foreground">{user.position}</p>
      {user.districts.length > 0 && (
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {user.districts.map((d) => d.name_uz).join(', ')}
        </p>
      )}
    </div>
  )
}

export function EmployeesPage() {
  const [page, setPage] = useState(1)
  const employees = useEmployees(page)

  if (employees.error) return <ErrorScreen error={employees.error} />

  return (
    <div>
      <header className="sticky top-0 z-10 border-b border-border bg-background px-4 py-3">
        <h1 className="text-lg font-semibold">Hodimlar</h1>
        {employees.data && (
          <p className="text-sm text-muted-foreground">Jami {employees.data.total} ta</p>
        )}
      </header>

      {employees.isLoading ? (
        <div className="space-y-3 p-4">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : !employees.data || employees.data.items.length === 0 ? (
        <EmptyScreen title="Hodimlar yo'q" />
      ) : (
        <>
          <div className="animate-fade-in">
            {employees.data.items.map((user) => (
              <EmployeeRow key={user.id} user={user} />
            ))}
          </div>

          {employees.data.pages > 1 && (
            <div className="flex items-center justify-center gap-3 py-4">
              <Button
                size="sm"
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Oldingi
              </Button>
              <span className="text-sm text-muted-foreground">
                {employees.data.page}/{employees.data.pages}
              </span>
              <Button
                size="sm"
                variant="secondary"
                disabled={page >= employees.data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Keyingi
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
