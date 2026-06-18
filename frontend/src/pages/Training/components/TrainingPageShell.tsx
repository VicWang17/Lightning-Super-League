import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { SegmentedTabs } from './SegmentedTabs'
import '../../../styles/training-system.css'

interface TrainingPageShellProps {
  title?: string
  subtitle?: string
  children: ReactNode
  actionBar?: ReactNode
  spacious?: boolean
}

export function TrainingPageShell({
  children,
  actionBar,
}: TrainingPageShellProps) {
  const navigate = useNavigate()

  return (
    <div className="training-console-page">
      <main style={{ marginTop: 16 }}>
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors"
          >
            返回上一页
          </button>
          {actionBar && <div className="flex items-center gap-3">{actionBar}</div>}
        </div>
        <SegmentedTabs />
        {children}
      </main>
    </div>
  )
}
