'use client'

import { RankBadge, StatusBadge, RankTierColor } from '@/components/shared/StatusBadge'
import { LANE_COLORS, LANE_ICONS } from '@/lib/constants'

interface Player {
  player_id: string
  name?: string
  full_name?: string
  email?: string
  current_rank: string
  current_stars: number
  highest_rank: string
  highest_stars: number
  skill_score: number
  role_flexibility_score: number
  primary_lane: string
  secondary_lane?: string
  primary_lane_comfort: number
  status?: string
  rank?: number
  skill_score_breakdown?: Record<string, any>
  role_flexibility_breakdown?: Record<string, any>
  lane_capabilities?: Record<string, number>
}

interface UserRankingCardProps {
  rank: number
  total: number
  player: Player
}

const pct = (val: number, total: number) => (total > 0 ? `${((val / total) * 100).toFixed(1)}%` : '0.0%')

export default function UserRankingCard({ rank, total, player }: UserRankingCardProps) {
  const skillTotal = player.skill_score || 0
  const skillBreakdown = player.skill_score_breakdown || {}
  const roleBreakdown = player.role_flexibility_breakdown || {}

  return (
    <div className="animate-slide-up">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-600/10 p-2.5">
          <span className="text-2xl">🏆</span>
        </div>
        <div>
          <h2 className="text-2xl font-bold text-white">Peringkat Saya</h2>
          <p className="text-sm text-gray-400">Total {total} peserta</p>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-surface-900/80 p-6 backdrop-blur-xl">
        <div className="mb-6 flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-600/20">
            <span className="text-2xl font-bold text-brand-400">{rank}</span>
          </div>
          <div>
            <p className="text-2xl font-bold text-white">{player.full_name || player.name || player.player_id}</p>
            <p className="text-sm text-gray-400">{player.email}</p>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4 text-center">
            <p className="text-xs text-gray-400">Peringkat</p>
            <p className="text-3xl font-bold text-brand-400">{rank}</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4 text-center">
            <p className="text-xs text-gray-400">Total Peserta</p>
            <p className="text-3xl font-bold text-white">{total}</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4 text-center">
            <p className="text-xs text-gray-400">Status</p>
            <div className="mt-2 flex justify-center">
              <StatusBadge status={player.status} rank={rank} qualifiedCount={total} />
            </div>
          </div>
          <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4 text-center">
            <p className="text-xs text-gray-400">Skill Score</p>
            <p className="text-3xl font-bold text-brand-400">{player.skill_score?.toFixed(1) || '0.0'}</p>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-400">Rank Saat Ini</p>
            <p className={`font-semibold ${RankTierColor(player.current_rank)}`}>
              {player.current_rank} ({player.current_stars} bintang)
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Rank Tertinggi</p>
            <p className={`font-semibold ${RankTierColor(player.highest_rank)}`}>
              {player.highest_rank} ({player.highest_stars} bintang)
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Lane Utama</p>
            <p className="font-semibold text-white">{player.primary_lane}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Fleksibilitas Peran</p>
            <p className="font-semibold text-white">{player.role_flexibility_score?.toFixed(0) || '0'}%</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs text-gray-400">Rincian Skor Keterampilan</p>
              <p className="text-xs font-bold text-brand-400">Total: {skillTotal.toFixed(2)}</p>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Rank Saat Ini</span>
                <span className="text-white">{(skillBreakdown.components?.current_rank?.raw_score || 0).toFixed(2)} ({pct(skillBreakdown.components?.current_rank?.raw_score || 0, skillTotal)})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Bintang Rank Saat Ini</span>
                <span className="text-white">{(skillBreakdown.components?.current_star?.raw_score || 0).toFixed(2)} ({pct(skillBreakdown.components?.current_star?.raw_score || 0, skillTotal)})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Rank Tertinggi</span>
                <span className="text-white">{(skillBreakdown.components?.highest_rank?.raw_score || 0).toFixed(2)} ({pct(skillBreakdown.components?.highest_rank?.raw_score || 0, skillTotal)})</span>
              </div>
              <div className="flex justify-between border-t border-white/10 pt-1">
                <span className="text-brand-400">Bintang Rank Tertinggi</span>
                <span className="font-bold text-brand-400">{(skillBreakdown.components?.highest_star?.raw_score || 0).toFixed(2)} ({pct(skillBreakdown.components?.highest_star?.raw_score || 0, skillTotal)})</span>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs text-gray-400">Rincian Fleksibilitas Peran</p>
              <p className="text-xs font-bold text-brand-400">Total: {player.role_flexibility_score?.toFixed(1) || '0.0'}%</p>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Kenyamanan Lane Utama</span>
                <span className="text-white">{roleBreakdown.primary_comfort || 0}/5 ({roleBreakdown.normalized_primary?.toFixed?.(1) ?? '0.0'}%)</span>
              </div>
              {roleBreakdown.secondary_comfort && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Kenyamanan Lane 2</span>
                  <span className="text-white">{roleBreakdown.secondary_comfort}/5</span>
                </div>
              )}
              <div className="flex justify-between border-t border-white/10 pt-1">
                <span className="text-brand-400">Kontribusi Lane Utama (70%)</span>
                <span className="text-white">{((roleBreakdown.normalized_primary || 0) * 0.7).toFixed(2)}</span>
              </div>
              {roleBreakdown.secondary_comfort && (
                <div className="flex justify-between">
                  <span className="text-brand-400">Kontribusi Lane 2 (30%)</span>
                  <span className="text-white">{((5.0 - (roleBreakdown.secondary_comfort || 0)) / 5.0 * 0.3 * 100).toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between border-t border-white/10 pt-1">
                <span className="text-brand-400">Skor Fleksibilitas</span>
                <span className="font-bold text-brand-400">{player.role_flexibility_score?.toFixed?.(1) ?? '0.0'}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
