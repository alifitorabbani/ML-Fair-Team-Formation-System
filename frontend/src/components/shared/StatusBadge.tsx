'use client'

import { SYSTEM_STATE_LABEL, RANK_TIER_COLORS } from '@/lib/constants'

export function SystemStateBadge({ state }: { state: string }) {
  const meta = SYSTEM_STATE_LABEL[state] || { label: state, color: 'bg-gray-500/20 text-gray-300 border-gray-500/30' }

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${meta.color}`}>
      {meta.label}
    </span>
  )
}

export function RankBadge({ rank, size = 'md' }: { rank: number; size?: 'sm' | 'md' }) {
  const sizeClasses = size === 'sm' ? 'h-8 w-8 text-xs' : 'h-10 w-10 text-sm'

  if (rank === 1) {
    return (
      <span className={`inline-flex items-center justify-center rounded-full bg-amber-500/15 font-bold text-amber-300 ${sizeClasses}`}>
        🥇
      </span>
    )
  }
  if (rank === 2) {
    return (
      <span className={`inline-flex items-center justify-center rounded-full bg-gray-300/15 font-bold text-gray-300 ${sizeClasses}`}>
        🥈
      </span>
    )
  }
  if (rank === 3) {
    return (
      <span className={`inline-flex items-center justify-center rounded-full bg-amber-700/15 font-bold text-amber-600 ${sizeClasses}`}>
        🥉
      </span>
    )
  }

  return (
    <span className={`inline-flex items-center justify-center rounded-full bg-white/5 font-bold text-gray-300 ${sizeClasses}`}>
      #{rank}
    </span>
  )
}

export function RankTierColor(rank: string) {
  return RANK_TIER_COLORS[rank] || 'text-gray-400'
}

export function StatusBadge({ status, rank, qualifiedCount }: { status?: string; rank?: number; qualifiedCount?: number }) {
  if (!status) return null

  const isQualified = status === 'QUALIFIED' || (rank !== undefined && qualifiedCount !== undefined && rank <= qualifiedCount)

  if (isQualified) {
    return (
      <span className="inline-flex items-center rounded-full border border-green-500/30 bg-green-500/10 px-2.5 py-0.5 text-xs font-medium text-green-300">
        Lolos
      </span>
    )
  }

  if (status === 'ELIMINATED') {
    return (
      <span className="inline-flex items-center rounded-full border border-brand-500/30 bg-brand-500/10 px-2.5 py-0.5 text-xs font-medium text-brand-300">
        Gugur
      </span>
    )
  }

  if (status === 'PAID') {
    return (
      <span className="inline-flex items-center rounded-full border border-green-500/30 bg-green-500/10 px-2.5 py-0.5 text-xs font-medium text-green-300">
        Terverifikasi
      </span>
    )
  }

  if (status === 'PENDING') {
    return (
      <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-300">
        Menunggu
      </span>
    )
  }

  return (
    <span className="inline-flex items-center rounded-full border border-gray-500/30 bg-gray-500/10 px-2.5 py-0.5 text-xs font-medium text-gray-300">
      {status}
    </span>
  )
}
