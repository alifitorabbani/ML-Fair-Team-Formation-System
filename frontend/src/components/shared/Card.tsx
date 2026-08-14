'use client'

import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  onClick?: () => void
}

export default function Card({ children, className = '', hover = false, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={[
        'rounded-2xl border border-white/10 bg-surface-900/80 p-6 backdrop-blur-xl transition-all duration-200',
        hover ? 'hover:border-brand-500/40 hover:shadow-brand hover:-translate-y-0.5 cursor-pointer' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  )
}
