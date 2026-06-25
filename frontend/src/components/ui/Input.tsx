import { InputHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      className,
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`

    const baseStyles =
      'fresh-input block w-full border-2 bg-white/85 text-[#173126] placeholder-[#7B927F] transition-all duration-200 focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed'

    const stateStyles = error
      ? 'border-[#FF6F59] focus:border-[#FF6F59] focus:ring-[#FF6F59]/20'
      : 'border-[#1F5F43]/45 focus:border-[#1F5F43] focus:ring-[#59C7EE]/25'

    const sizeStyles = leftIcon || rightIcon ? 'py-2.5' : 'py-2.5'
    const iconPadding = {
      left: leftIcon ? 'pl-10' : 'pl-4',
      right: rightIcon ? 'pr-10' : 'pr-4',
    }

    return (
      <div className={clsx(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-black text-[#173126] mb-2"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#466353]">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              baseStyles,
              stateStyles,
              sizeStyles,
              iconPadding.left,
              iconPadding.right,
              className
            )}
            disabled={disabled}
            {...props}
          />
          {rightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#466353]">
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-1.5 text-sm font-semibold text-[#FF6F59]">{error}</p>
        )}
        {!error && helperText && (
          <p className="mt-1.5 text-sm font-semibold text-[#466353]">{helperText}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input
