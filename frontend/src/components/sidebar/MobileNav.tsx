import { NavLink } from 'react-router-dom'
import { History, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/sessions', icon: History, label: 'Sessions' },
  { to: '/settings', icon: Settings, label: 'Settings' },
] as const

export function MobileNav() {
  return (
    <nav className="md:hidden flex border-t border-border bg-card">
      {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              'flex-1 flex flex-col items-center py-2 gap-0.5 text-xs transition-colors',
              isActive ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
            )
          }
        >
          <Icon className="h-5 w-5" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
