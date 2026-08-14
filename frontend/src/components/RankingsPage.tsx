'use client'

import React, { useState, useEffect } from 'react'
import { getMyRanking, adminRankingPreview, getAllRankings } from '@/lib/api'
import { Trophy, User, Star, Shield, Target, ChevronDown, ChevronUp, Clock, Medal } from 'lucide-react'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import UserRankingCard from '@/components/shared/UserRankingCard'
import { LANE_COLORS, LANE_ICONS } from '@/lib/constants'
import { useAuthToken, useUserSession } from '@/lib/hooks/useAuth'

function getUserRole(): 'admin' | 'user' | null {
  const session = useUserSession()
  return session?.role || null
}

const pct = (val: number, total: number) => (total > 0 ? `${((val / total) * 100).toFixed(1)}%` : '0.0%')

export default function RankingsPage() {
  const [rankings, setRankings] = useState<any[]>([])
  const [myRanking, setMyRanking] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'rank' | 'skill' | 'rank_tier'>('rank')
  const [expandedPlayer, setExpandedPlayer] = useState<string | null>(null)
  const [showStatus, setShowStatus] = useState(true)
  const role = getUserRole()
  const token = useAuthToken()

  useEffect(() => {
    if (!role || !token) return

    const loadRankings = async () => {
      try {
        setLoading(true)
        setError(null)

        if (role === 'admin') {
          const data = await adminRankingPreview(token)
          setRankings(data.rankings || [])
        } else {
          const [allData, myData] = await Promise.all([
            getAllRankings(token).catch(() => ({ rankings: [] })),
            getMyRanking(token).catch(() => null),
          ])
          setRankings(allData.rankings || [])
          setMyRanking(myData)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Gagal memuat perankingan')
      } finally {
        setLoading(false)
      }
    }

    loadRankings()
  }, [role, token])

  const filteredRankings = rankings
    .filter((p) => {
      const query = searchQuery.toLowerCase()
      return (
        p.full_name?.toLowerCase().includes(query) ||
        p.name?.toLowerCase().includes(query) ||
        p.player_id.toLowerCase().includes(query) ||
        p.username?.toLowerCase().includes(query) ||
        p.current_rank.toLowerCase().includes(query) ||
        p.primary_lane.toLowerCase().includes(query)
      )
    })
    .sort((a, b) => {
      if (sortBy === 'rank') return (a.rank || 0) - (b.rank || 0)
      if (sortBy === 'skill') return b.skill_score - a.skill_score
      if (sortBy === 'rank_tier') {
        const rankOrder: Record<string, number> = {
          'Mythical Immortal': 10,
          'Mythical Glory': 9,
          'Mythical Honor': 8,
          Mythic: 7,
          Legend: 6,
          Epic: 5,
          Grandmaster: 4,
          Master: 3,
          Elite: 2,
          Warrior: 1,
        }
        return (rankOrder[b.current_rank] || 0) - (rankOrder[a.current_rank] || 0)
      }
      return 0
    })

  if (loading) {
    return (
      <Card>
        <LoadingSpinner text="Memuat perankingan..." />
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <ErrorMessage title="Error" message={error} />
      </Card>
    )
  }

  if (role === 'user' && myRanking && !searchQuery) {
    return (
      <div className="animate-fade-in space-y-4">
        <UserRankingCard rank={myRanking.rank} total={myRanking.total} player={myRanking.player} />

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Perankingan Semua Pemain</h2>
              <p className="text-xs text-gray-400">Ranking Anda ditandai</p>
            </div>
          </div>
          <div className="overflow-x-auto rounded-xl border border-white/5">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-xs uppercase text-gray-400">
                  <th className="px-3 py-3 text-center">Rank</th>
                  <th className="px-3 py-3">Nama Lengkap</th>
                  <th className="px-3 py-3">Username ML</th>
                  <th className="px-3 py-3 text-center">Rank Saat Ini</th>
                  <th className="px-3 py-3 text-center">Bintang</th>
                  <th className="px-3 py-3 text-center">Rank Tertinggi</th>
                  <th className="px-3 py-3 text-center">Bintang</th>
                  <th className="px-3 py-3">Lane #1</th>
                  <th className="px-3 py-3 text-center">Kenya. Lane #1</th>
                  <th className="px-3 py-3">Lane #2</th>
                  <th className="px-3 py-3 text-center">Kenya. Lane #2</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredRankings.map((player) => {
                  const globalRank = player.rank || 0
                  const isMe = player.is_current_user
                  const isExpanded = expandedPlayer === player.player_id

                  return (
                    <React.Fragment key={player.player_id}>
                      <tr key={`${player.player_id}-row`} className={`transition ${isMe ? 'bg-brand-500/10' : 'hover:bg-white/5'}`}>
                        <td className="px-3 py-3 text-center">
                          <button
                            type="button"
                            onClick={() => setExpandedPlayer(isExpanded ? null : player.player_id)}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold transition hover:scale-105"
                          >
                            <span
                              className={`inline-flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold ${
                                globalRank === 1
                                  ? 'bg-amber-500/15 text-amber-300'
                                  : globalRank === 2
                                  ? 'bg-gray-300/15 text-gray-200'
                                  : globalRank === 3
                                  ? 'bg-amber-700/15 text-amber-600'
                                  : isMe
                                  ? 'bg-brand-500/20 text-brand-300'
                                  : 'bg-white/5 text-gray-300'
                              }`}
                            >
                              {globalRank === 1
                                ? '🥇'
                                : globalRank === 2
                                ? '🥈'
                                : globalRank === 3
                                ? '🥉'
                                : isMe
                                ? '⭐'
                                : `#${globalRank}`}
                            </span>
                          </button>
                        </td>
                        <td className="px-3 py-3">
                          <p className={`font-medium ${isMe ? 'text-brand-300' : 'text-white'}`}>{player.full_name || player.name || player.player_id}</p>
                        </td>
                        <td className="px-3 py-3 text-xs text-gray-300">@{player.username || '-'}</td>
                        <td className="px-3 py-3 text-center">
                          <span className={`font-semibold ${player.current_rank ? 'text-white' : 'text-gray-500'}`}>{player.current_rank || '-'}</span>
                        </td>
                        <td className="px-3 py-3 text-center">
                          <div className="flex items-center justify-center gap-1 text-gray-300">
                            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                            <span className="text-xs">{player.current_stars}</span>
                          </div>
                        </td>
                        <td className="px-3 py-3 text-center">
                          <span className="font-semibold text-white">{player.highest_rank || '-'}</span>
                        </td>
                        <td className="px-3 py-3 text-center">
                          <div className="flex items-center justify-center gap-1 text-gray-300">
                            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                            <span className="text-xs">{player.highest_stars}</span>
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.primary_lane] || 'bg-gray-600'}`}>
                            {player.primary_lane}
                          </span>
                        </td>
                        <td className={`px-3 py-3 text-center text-xs ${(player.primary_lane_comfort ?? 0) <= 2 ? 'text-green-400' : (player.primary_lane_comfort ?? 0) === 3 ? 'text-amber-400' : 'text-red-400'}`}>
                          {player.primary_lane_comfort ?? 0}/5
                        </td>
                        <td className="px-3 py-3">
                          {player.secondary_lane ? (
                            <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.secondary_lane] || 'bg-gray-600'}`}>
                              {player.secondary_lane}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">-</span>
                          )}
                        </td>
                        <td className={`px-3 py-3 text-center text-xs ${(player.secondary_lane_comfort ?? 0) <= 2 ? 'text-green-400' : (player.secondary_lane_comfort ?? 0) === 3 ? 'text-amber-400' : 'text-red-400'}`}>
                          {player.secondary_lane_comfort ?? 0}/5
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr key={`${player.player_id}-detail`} className="border-b border-white/5 bg-white/5">
                          <td colSpan={showStatus ? 12 : 11} className="px-3 py-4">
                            <div className="grid grid-cols-2 gap-4 text-xs">
                              <div>
                                <div className="mb-2 flex items-center justify-between">
                                  <p className="text-gray-400">Rincian Skor Keterampilan</p>
                                  <p className="text-xs font-bold text-brand-400">Total: {player.skill_score?.toFixed(2) || '0.00'}</p>
                                </div>
                                <div className="space-y-1">
                                  <div className="flex justify-between">
                                    <span className="text-gray-400">Rank Saat Ini</span>
                                    <span className="text-white">{(player.skill_score_breakdown?.components?.current_rank?.raw_score || 0).toFixed(2)} ({pct(player.skill_score_breakdown?.components?.current_rank?.raw_score || 0, player.skill_score || 1)})</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-400">Bintang Rank Saat Ini</span>
                                    <span className="text-white">{(player.skill_score_breakdown?.components?.current_star?.raw_score || 0).toFixed(2)} ({pct(player.skill_score_breakdown?.components?.current_star?.raw_score || 0, player.skill_score || 1)})</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-400">Rank Tertinggi</span>
                                    <span className="text-white">{(player.skill_score_breakdown?.components?.highest_rank?.raw_score || 0).toFixed(2)} ({pct(player.skill_score_breakdown?.components?.highest_rank?.raw_score || 0, player.skill_score || 1)})</span>
                                  </div>
                                  <div className="flex justify-between border-t border-white/10 pt-1">
                                    <span className="text-brand-400">Bintang Rank Tertinggi</span>
                                    <span className="font-bold text-brand-400">{(player.skill_score_breakdown?.components?.highest_star?.raw_score || 0).toFixed(2)} ({pct(player.skill_score_breakdown?.components?.highest_star?.raw_score || 0, player.skill_score || 1)})</span>
                                  </div>
                                </div>
                              </div>
                              <div>
                                <div className="mb-2 flex items-center justify-between">
                                  <p className="text-gray-400">Rincian Fleksibilitas Peran</p>
                                  <p className="text-xs font-bold text-brand-400">Total: {player.role_flexibility_score?.toFixed(1) || '0.0'}%</p>
                                </div>
                                <div className="space-y-1">
                                  <div className="flex justify-between">
                                    <span className="text-gray-400">Kenyamanan Lane Utama</span>
                                    <span className="text-white">{player.role_flexibility_breakdown?.primary_comfort || 0}/5 ({(player.role_flexibility_breakdown?.normalized_primary || 0).toFixed(1)}%)</span>
                                  </div>
                                  {player.role_flexibility_breakdown?.secondary_comfort && (
                                    <div className="flex justify-between">
                                      <span className="text-gray-400">Kenyamanan Lane 2</span>
                                      <span className="text-white">{player.role_flexibility_breakdown.secondary_comfort}/5</span>
                                    </div>
                                  )}
                                  <div className="flex justify-between border-t border-white/10 pt-1">
                                    <span className="text-brand-400">Kontribusi Lane Utama (70%)</span>
                                    <span className="text-white">{((player.role_flexibility_breakdown?.normalized_primary || 0) * 0.7).toFixed(2)}</span>
                                  </div>
                                  {player.role_flexibility_breakdown?.secondary_comfort && (
                                    <div className="flex justify-between">
                                      <span className="text-brand-400">Kontribusi Lane 2 (30%)</span>
                                      <span className="text-white">{((5.0 - (player.role_flexibility_breakdown?.secondary_comfort || 0)) / 5.0 * 0.3 * 100).toFixed(2)}</span>
                                    </div>
                                  )}
                                  <div className="flex justify-between border-t border-white/10 pt-1">
                                    <span className="text-brand-400">Skor Fleksibilitas</span>
                                    <span className="font-bold text-brand-400">{player.role_flexibility_score?.toFixed?.(1) ?? '0.0'}%</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
          {filteredRankings.length === 0 && (
            <div className="py-8 text-center text-sm text-gray-500">Tidak ada pemain yang cocok dengan pencarian "{searchQuery}"</div>
          )}
        </Card>
      </div>
    )
  }

  if (role === 'user' && !myRanking) {
    return (
      <Card>
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2.5 text-amber-400">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Ranking Belum Tersedia</h3>
            <p className="text-sm text-gray-400">Silakan tunggu admin melakukan generate ranking.</p>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <div className="animate-fade-in space-y-4">
      <Card>
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-brand-600/10 p-2.5 text-brand-400">
              <Trophy className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Perankingan Pemain</h2>
              <p className="text-xs text-gray-400">Total {rankings.length} pemain</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowStatus(!showStatus)}
              className="rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-xs font-medium text-gray-300 transition hover:border-brand-500/40 hover:text-white"
            >
              {showStatus ? 'Sembunyikan Status' : 'Tampilkan Status'}
            </button>
          </div>
        </div>

        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <div className="flex-1">
            <div className="relative">
              <Target className="absolute left-3 top-2.5 h-4 w-4 text-gray-500" />
              <input
                type="text"
                placeholder="Cari nama, ID, username, rank, atau lane..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-surface-950/60 py-2 pl-10 pr-4 text-sm text-white placeholder-gray-500 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
              />
            </div>
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="rounded-xl border border-white/10 bg-surface-950/60 px-4 py-2 text-sm text-white outline-none transition focus:border-brand-500"
          >
            <option value="rank">Urutkan: Ranking</option>
            <option value="skill">Urutkan: Skill Score</option>
            <option value="rank_tier">Urutkan: Rank Tier</option>
          </select>
        </div>

        <div className="overflow-x-auto rounded-xl border border-white/5">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 bg-white/5 text-xs uppercase text-gray-400">
                <th className="px-3 py-3 text-center">Rank</th>
                <th className="px-3 py-3">Nama Lengkap</th>
                <th className="px-3 py-3">Username ML</th>
                <th className="px-3 py-3 text-center">Rank Saat Ini</th>
                <th className="px-3 py-3 text-center">Bintang</th>
                <th className="px-3 py-3 text-center">Rank Tertinggi</th>
                <th className="px-3 py-3 text-center">Bintang</th>
                <th className="px-3 py-3">Lane #1</th>
                <th className="px-3 py-3 text-center">Kenya. Lane #1</th>
                <th className="px-3 py-3">Lane #2</th>
                <th className="px-3 py-3 text-center">Kenya. Lane #2</th>
                {showStatus && <th className="px-3 py-3 text-center">Status</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredRankings.map((player) => {
                const globalRank = player.rank || 0
                const isExpanded = expandedPlayer === player.player_id
                const isMe = player.is_current_user

                return (
                  <React.Fragment key={player.player_id}>
                    <tr key={`${player.player_id}-row`} className={`transition ${isMe ? 'bg-brand-500/10' : 'hover:bg-white/5'}`}>
                      <td className="px-3 py-3 text-center">
                        <button
                          type="button"
                          onClick={() => setExpandedPlayer(isExpanded ? null : player.player_id)}
                          className="inline-flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold transition hover:scale-105"
                        >
                          <span
                            className={`inline-flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold ${
                              globalRank === 1
                                ? 'bg-amber-500/15 text-amber-300'
                                : globalRank === 2
                                ? 'bg-gray-300/15 text-gray-200'
                                : globalRank === 3
                                ? 'bg-amber-700/15 text-amber-600'
                                : isMe
                                ? 'bg-brand-500/20 text-brand-300'
                                : 'bg-white/5 text-gray-300'
                            }`}
                          >
                            {globalRank === 1
                              ? '🥇'
                              : globalRank === 2
                              ? '🥈'
                              : globalRank === 3
                              ? '🥉'
                              : isMe
                              ? '⭐'
                              : `#${globalRank}`}
                          </span>
                        </button>
                      </td>
                      <td className="px-3 py-3">
                        <p className={`font-medium ${isMe ? 'text-brand-300' : 'text-white'}`}>{player.full_name || player.name || player.player_id}</p>
                      </td>
                      <td className="px-3 py-3 text-xs text-gray-300">@{player.username || '-'}</td>
                      <td className="px-3 py-3 text-center">
                        <span className={`font-semibold ${player.current_rank ? 'text-white' : 'text-gray-500'}`}>{player.current_rank || '-'}</span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <div className="flex items-center justify-center gap-1 text-gray-300">
                          <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                          <span className="text-xs">{player.current_stars}</span>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <span className="font-semibold text-white">{player.highest_rank || '-'}</span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <div className="flex items-center justify-center gap-1 text-gray-300">
                          <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                          <span className="text-xs">{player.highest_stars}</span>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.primary_lane] || 'bg-gray-600'}`}>
                          {player.primary_lane}
                        </span>
                      </td>
                      <td className={`px-3 py-3 text-center text-xs ${(player.primary_lane_comfort ?? 0) <= 2 ? 'text-green-400' : (player.primary_lane_comfort ?? 0) === 3 ? 'text-amber-400' : 'text-red-400'}`}>
                        {player.primary_lane_comfort ?? 0}/5
                      </td>
                      <td className="px-3 py-3">
                        {player.secondary_lane ? (
                          <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.secondary_lane] || 'bg-gray-600'}`}>
                            {player.secondary_lane}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-500">-</span>
                        )}
                      </td>
                      <td className={`px-3 py-3 text-center text-xs ${(player.secondary_lane_comfort ?? 0) <= 2 ? 'text-green-400' : (player.secondary_lane_comfort ?? 0) === 3 ? 'text-amber-400' : 'text-red-400'}`}>
                        {player.secondary_lane_comfort ?? 0}/5
                      </td>
                      {showStatus && (
                        <td className="px-3 py-3 text-center">
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                              player.status === 'QUALIFIED'
                                ? 'border border-green-500/30 bg-green-500/10 text-green-300'
                                : player.status === 'ELIMINATED'
                                ? 'border border-brand-500/30 bg-brand-500/10 text-brand-300'
                                : 'border border-gray-500/30 bg-gray-500/10 text-gray-300'
                            }`}
                          >
                            {player.status}
                          </span>
                        </td>
                      )}
                    </tr>
                    {isExpanded && (
                      <tr key={`${player.player_id}-detail`} className="border-b border-white/5 bg-white/5">
                        <td colSpan={showStatus ? 12 : 11} className="px-3 py-4">
                          <div className="grid grid-cols-2 gap-4 text-xs">
                            <div>
                              <p className="mb-2 text-gray-400">Rincian Skor Keterampilan</p>
                              <div className="space-y-1">
                                <div className="flex justify-between">
                                  <span className="text-gray-400">Rank Saat Ini</span>
                                  <span className="text-white">{pct(player.skill_score_breakdown?.components?.current_rank?.raw_score || 0, player.skill_score || 1)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-400">Bintang Rank Saat Ini</span>
                                  <span className="text-white">{pct(player.skill_score_breakdown?.components?.current_star?.raw_score || 0, player.skill_score || 1)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-400">Rank Tertinggi</span>
                                  <span className="text-white">{pct(player.skill_score_breakdown?.components?.highest_rank?.raw_score || 0, player.skill_score || 1)}</span>
                                </div>
                                <div className="flex justify-between border-t border-white/10 pt-1">
                                  <span className="text-brand-400">Bintang Rank Tertinggi</span>
                                  <span className="font-bold text-brand-400">{pct(player.skill_score_breakdown?.components?.highest_star?.raw_score || 0, player.skill_score || 1)}</span>
                                </div>
                              </div>
                            </div>
                            <div>
                              <p className="mb-2 text-gray-400">Rincian Fleksibilitas Peran</p>
                              <div className="space-y-1">
                                <div className="flex justify-between">
                                  <span className="text-gray-400">Kenyamanan Lane Utama</span>
                                  <span className="text-white">{player.role_flexibility_breakdown?.primary_comfort || 0}/5 ({(player.role_flexibility_breakdown?.normalized_primary || 0).toFixed(1)}%)</span>
                                </div>
                                {player.role_flexibility_breakdown?.secondary_comfort && (
                                  <div className="flex justify-between">
                                    <span className="text-gray-400">Kenyamanan Lane 2</span>
                                    <span className="text-white">{player.role_flexibility_breakdown.secondary_comfort}/5</span>
                                  </div>
                                )}
                                <div className="flex justify-between border-t border-white/10 pt-1">
                                  <span className="text-brand-400">Kontribusi Lane Utama (70%)</span>
                                  <span className="text-white">{((player.role_flexibility_breakdown?.normalized_primary || 0) * 0.7).toFixed(2)}</span>
                                </div>
                                {player.role_flexibility_breakdown?.secondary_comfort && (
                                  <div className="flex justify-between">
                                    <span className="text-brand-400">Kontribusi Lane 2 (30%)</span>
                                    <span className="text-white">{((5.0 - (player.role_flexibility_breakdown?.secondary_comfort || 0)) / 5.0 * 0.3 * 100).toFixed(2)}</span>
                                  </div>
                                )}
                                <div className="flex justify-between border-t border-white/10 pt-1">
                                  <span className="text-brand-400">Skor Fleksibilitas</span>
                                  <span className="font-bold text-brand-400">{player.role_flexibility_score?.toFixed?.(1) ?? '0.0'}%</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                      )}
                    </React.Fragment>
                  )
                })}
            </tbody>
          </table>
        </div>

        {filteredRankings.length === 0 && (
          <div className="py-8 text-center text-sm text-gray-500">Tidak ada pemain yang cocok dengan pencarian "{searchQuery}"</div>
        )}
      </Card>
    </div>
  )
}