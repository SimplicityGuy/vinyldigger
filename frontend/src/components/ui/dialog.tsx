import * as React from 'react'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/50"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />
      <div className="relative bg-background rounded-lg shadow-lg max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        {children}
      </div>
    </div>
  )
}

type DialogContentProps = React.HTMLAttributes<HTMLDivElement>

export function DialogContent({ className, children, ...props }: DialogContentProps) {
  return (
    <div className={cn('p-6', className)} {...props}>
      {children}
    </div>
  )
}

type DialogHeaderProps = React.HTMLAttributes<HTMLDivElement>

export function DialogHeader({ className, ...props }: DialogHeaderProps) {
  return <div className={cn('mb-4', className)} {...props} />
}

type DialogTitleProps = React.HTMLAttributes<HTMLHeadingElement>

export function DialogTitle({ className, ...props }: DialogTitleProps) {
  return <h2 className={cn('text-lg font-semibold', className)} {...props} />
}

type DialogDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>

export function DialogDescription({ className, ...props }: DialogDescriptionProps) {
  return <p className={cn('text-sm text-muted-foreground', className)} {...props} />
}

interface DialogCloseProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  onClose: () => void
}

export function DialogClose({ onClose, className, ...props }: DialogCloseProps) {
  return (
    <button
      type="button"
      onClick={onClose}
      className={cn(
        'absolute right-4 top-4 rounded-sm opacity-70 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:pointer-events-none',
        className
      )}
      {...props}
    >
      <X className="h-4 w-4" />
      <span className="sr-only">Close</span>
    </button>
  )
}
