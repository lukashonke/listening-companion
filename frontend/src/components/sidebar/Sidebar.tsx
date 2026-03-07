import { useState } from 'react'
import { History, Brain, ImageIcon, Settings, ChevronLeft, ChevronRight } from 'lucide-react'
import { NavItem } from './NavItem'
import { cn } from '@/lib/utils'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'

const NAV_ITEMS = [
  { to: '/sessions', icon: History, label: 'Sessions' },
  { to: '/memory', icon: Brain, label: 'Memory' },
  { to: '/images', icon: ImageIcon, label: 'Images' },
  { to: '/settings', icon: Settings, label: 'Settings' },
] as const

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <TooltipProvider delay={0}>
      <aside
        className={cn(
          'hidden md:flex flex-col border-r border-border bg-card transition-all duration-200',
          collapsed ? 'w-14' : 'w-52'
        )}
      >
        {/* Brand */}
        <div
          className={cn(
            'flex items-center h-14 px-4 gap-2 overflow-hidden',
            collapsed && 'justify-center px-0'
          )}
        >
          {!collapsed && (
            <span className="font-semibold text-sm text-foreground truncate whitespace-nowrap">
              Listening Companion
            </span>
          )}
        </div>

        <Separator />

        {/* Navigation */}
        <nav className="flex-1 flex flex-col gap-1 p-2">
          {NAV_ITEMS.map((item) => (
            <NavItem key={item.to} {...item} collapsed={collapsed} />
          ))}
        </nav>

        <Separator />

        {/* Collapse toggle */}
        <div className={cn('p-2', collapsed ? 'flex justify-center' : 'flex justify-end')}>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed((c) => !c)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>
      </aside>
    </TooltipProvider>
  )
}
