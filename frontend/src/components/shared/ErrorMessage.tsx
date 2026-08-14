'use client'

type ErrorVariant = 'error' | 'warning' | 'success' | 'info'

interface ErrorMessageProps {
  title?: string
  message: string
  variant?: ErrorVariant
}

const VARIANT_STYLES: Record<ErrorVariant, string> = {
  error: 'border-brand-500/40 bg-brand-950/60 text-brand-200',
  warning: 'border-amber-500/40 bg-amber-950/60 text-amber-200',
  success: 'border-green-500/40 bg-green-950/60 text-green-200',
  info: 'border-blue-500/40 bg-blue-950/60 text-blue-200',
}

export default function ErrorMessage({ title, message, variant = 'error' }: ErrorMessageProps) {
  return (
    <div className={`rounded-xl border px-4 py-3 ${VARIANT_STYLES[variant]}`}>
      {title && <p className="mb-1 text-xs font-semibold uppercase tracking-wider opacity-80">{title}</p>}
      <p className="text-sm leading-relaxed">{message}</p>
    </div>
  )
}
