import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  src?: string
  alt?: string
  name?: string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  status?: 'online' | 'offline' | 'away' | 'busy'
  fallback?: React.ReactNode
}

const Avatar = forwardRef<HTMLDivElement, AvatarProps>(
  (
    {
      src,
      alt = '',
      name,
      size = 'md',
      status,
      fallback,
      className,
      ...props
    },
    ref
  ) => {
    const sizes = {
      xs: 'w-6 h-6 text-xs',
      sm: 'w-8 h-8 text-sm',
      md: 'w-10 h-10 text-base',
      lg: 'w-12 h-12 text-lg',
      xl: 'w-16 h-16 text-xl',
    }

    const statusSizes = {
      xs: 'w-1.5 h-1.5',
      sm: 'w-2 h-2',
      md: 'w-2.5 h-2.5',
      lg: 'w-3 h-3',
      xl: 'w-3.5 h-3.5',
    }

    const statusColors = {
      online: 'bg-[#4ADE80]',
      offline: 'bg-[#4B4B6A]',
      away: 'bg-[#FCD34D]',
      busy: 'bg-[#EF4444]',
    }

    // 生成默认头像（基于名字的首字母）
    const getInitials = (name: string) => {
      return name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    }

    // 根据名字生成颜色
    const getColorFromName = (name: string) => {
      const colors = [
        'bg-[#0D7377]',
        'bg-[#3B82F6]',
        'bg-[#8B5CF6]',
        'bg-[#EC4899]',
        'bg-[#F97316]',
        'bg-[#10B981]',
      ]
      let hash = 0
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash)
      }
      return colors[Math.abs(hash) % colors.length]
    }

    return (
      <div ref={ref} className="relative inline-block" {...props}>
        <div
          className={clsx(
            'rounded-none overflow-hidden flex items-center justify-center border-2 border-[#2D2D44]',
            sizes[size],
            !src && name && getColorFromName(name),
            !src && !name && 'bg-[#2D2D44]',
            className
          )}
        >
          {src ? (
            <img
              src={src}
              alt={alt}
              className="w-full h-full object-cover"
              onError={(e) => {
                // 图片加载失败时显示 fallback
                ;(e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          ) : fallback ? (
            fallback
          ) : name ? (
            <span className="font-medium text-white">{getInitials(name)}</span>
          ) : (
            <svg
              className="w-1/2 h-1/2 text-[#8B8BA7]"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
        {status && (
          <span
            className={clsx(
              'absolute bottom-0 right-0 rounded-none border-2 border-[#0A0A0F]',
              statusSizes[size],
              statusColors[status]
            )}
          />
        )}
      </div>
    )
  }
)

Avatar.displayName = 'Avatar'

export default Avatar
