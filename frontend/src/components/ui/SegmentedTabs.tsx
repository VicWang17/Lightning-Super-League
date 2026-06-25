import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'

export interface RouteTab {
  path: string
  label: string
}

export interface StateTab {
  value: string
  label: string
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
    'px-4 py-2 font-black text-sm transition-all duration-200 flex items-center gap-2 border-2'
  const inactive =
    'text-[#466353] hover:text-[#173126] hover:bg-white border-[#1F5F43]/20 bg-white/45'
  const active =
    'bg-[#FFC247] text-[#173126] border-[#1F5F43] shadow-[3px_3px_0_rgba(31,95,67,0.18)]'

  return (
    <nav className="flex flex-wrap gap-2 mb-6">
      {tabs.map((tab) => {
        if (mode === 'route') {
          const routeTab = tab as RouteTab
          return (
            <NavLink
              key={routeTab.path}
              to={routeTab.path}
              className={({ isActive }) => clsx(base, isActive ? active : inactive)}
            >
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
            {stateTab.label}
          </button>
        )
      })}
    </nav>
  )
}
