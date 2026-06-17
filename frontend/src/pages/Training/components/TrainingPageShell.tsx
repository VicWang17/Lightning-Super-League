import type { ReactNode } from 'react'
import { TrainingTabs } from './TrainingTabs'
import '../../../styles/training-system.css'

interface TrainingPageShellProps {
  title: string
  subtitle?: string
  children: ReactNode
  actionBar?: ReactNode
  spacious?: boolean
}

export function TrainingPageShell({
  title,
  subtitle,
  children,
  actionBar,
  spacious = false,
}: TrainingPageShellProps) {
  return (
    <div className="training-console-page">
      <section className={`training-hero ${spacious ? 'training-hero--spacious' : ''}`}>
        <div className="training-hero-copy">
          <div className="training-chip">
            <span />
            训练场
          </div>
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actionBar && <div className="training-command-strip">{actionBar}</div>}
      </section>
      <main style={{ marginTop: 16 }}>
        <TrainingTabs />
        {children}
      </main>
    </div>
  )
}
