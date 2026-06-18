import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import type { ComponentType } from 'react'

export interface RouteTab {
  path: string
  label: string
  icon?: ComponentType<{ className?: string }>
}

export interface StateTab {
  value: string
  label: string
  icon?: ComponentType<{ className?: string }>
}

export type SegmentedTab = RouteTab | StateTab

interface RouteModeProps {
  tabs: RouteTab[]
  mode: 'route'
}

interface StateModeProps {
  tabs: StateTab[]
  mode?: 'state'
  value?: string
  onChange?: (value: string) => void
}

export type SegmentedTabsProps = RouteModeProps | StateModeProps

export function SegmentedTabs(props: SegmentedTabsProps) {
  const { tabs, mode } = props

  const base =
    'px-4 py-2 font-medium text-sm transition-all duration-200 flex items-center gap-2'
  const inactive =
    'text-text-secondary hover:text-text-primary hover:bg-surface-hover border-2 border-transparent'
  const active =
    'bg-[#C6F135] text-[#0A0A0F] border-2 border-transparent font-bold shadow-pixel-green'

  return (
    <nav className="flex flex-wrap gap-2 mb-6">
      {tabs.map((tab) => {
        const Icon = tab.icon

        if (mode === 'route') {
          const routeTab = tab as RouteTab
          return (
            <NavLink
              key={routeTab.path}
              to={routeTab.path}
              end
              className={({ isActive }) => clsx(base, isActive ? active : inactive)}
            >
              {Icon && <Icon className="w-4 h-4" />}
              {routeTab.label}
            </NavLink>
          )
        }

        const stateTab = tab as StateTab
        const isActive =
          'value' in props ? props.value === stateTab.value : false

        return (
          <button
            key={stateTab.value}
            type="button"
            className={clsx(base, isActive ? active : inactive)}
            onClick={() =>
              'onChange' in props && props.onChange?.(stateTab.value)
            }
          >
            {Icon && <Icon className="w-4 h-4" />}
            {stateTab.label}
          </button>
        )
      })}
    </nav>
  )
}
