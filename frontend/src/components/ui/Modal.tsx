import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { clsx } from 'clsx'
import { X } from 'lucide-react'
import Button from './Button'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  description?: string
  children: React.ReactNode
  footer?: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  showCloseButton?: boolean
  closeOnOverlayClick?: boolean
}

const Modal = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  showCloseButton = true,
  closeOnOverlayClick = true,
}: ModalProps) => {
  const sizes = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    full: 'max-w-full mx-4',
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-50"
        onClose={closeOnOverlayClick ? onClose : () => {}}
      >
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/60" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel
                className={clsx(
                  'w-full transform overflow-hidden bg-[#12121A] border-2 border-[#2D2D44] text-left align-middle shadow-pixel-lg transition-all',
                  sizes[size]
                )}
              >
                {/* Header */}
                {(title || showCloseButton) && (
                  <div className="flex items-start justify-between px-6 py-4 border-b-2 border-[#2D2D44]">
                    <div>
                      {title && (
                        <Dialog.Title
                          as="h3"
                          className="text-lg font-semibold text-[#E2E2F0]"
                        >
                          {title}
                        </Dialog.Title>
                      )}
                      {description && (
                        <Dialog.Description className="mt-1 text-sm text-[#8B8BA7]">
                          {description}
                        </Dialog.Description>
                      )}
                    </div>
                    {showCloseButton && (
                      <button
                        onClick={onClose}
                        className="ml-4 text-[#8B8BA7] hover:text-[#E2E2F0] transition-colors"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                )}

                {/* Content */}
                <div className="px-6 py-4">{children}</div>

                {/* Footer */}
                {footer && (
                  <div className="flex items-center justify-end gap-3 px-6 py-4 border-t-2 border-[#2D2D44] bg-[#0A0A0F]/50">
                    {footer}
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

// 预设的确认模态框
export interface ConfirmModalProps extends Omit<ModalProps, 'footer'> {
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  confirmVariant?: 'primary' | 'danger'
  isLoading?: boolean
}

const ConfirmModal = ({
  confirmText = '确认',
  cancelText = '取消',
  onConfirm,
  confirmVariant = 'primary',
  isLoading = false,
  children,
  ...props
}: ConfirmModalProps) => {
  const footer = (
    <>
      <Button variant="ghost" onClick={props.onClose} disabled={isLoading}>
        {cancelText}
      </Button>
      <Button
        variant={confirmVariant}
        onClick={onConfirm}
        isLoading={isLoading}
      >
        {confirmText}
      </Button>
    </>
  )

  return <Modal {...props} footer={footer}>{children}</Modal>
}

export { Modal, ConfirmModal }
export default Modal
