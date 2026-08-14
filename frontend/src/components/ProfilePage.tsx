'use client'

import { useState, useEffect } from 'react'
import { getMyRanking, getMyTeam } from '@/lib/api'
import { User, Mail, Trophy, Star, Shield, Clock, Swords, Crosshair, Crown, Zap, TrendingUp } from 'lucide-react'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import UserRankingCard from '@/components/shared/UserRankingCard'
import { LANE_COLORS } from '@/lib/constants'
import { useAuthToken, useUserSession } from '@/lib/hooks/useAuth'
import { StatusBadge } from '@/components/shared/StatusBadge'

export default function ProfilePage({ token: propToken }: { token?: string } = {}) {
  const session = useUserSession()
  const token = propToken || session?.token
  const [ranking, setRanking] = useState<any>(null)
  const [team, setTeam] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return

    const load = async () => {
      try {
        setLoading(true)
        const [rankingData, teamData] = await Promise.all([
          getMyRanking(token).catch(() => null),
          getMyTeam(token).catch(() => null),
        ])
        setRanking(rankingData)
        setTeam(teamData)
      } catch {
        setError('Gagal memuat profil')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [token])

  if (loading) {
    return (
      <Card>
        <LoadingSpinner text="Memuat profil..." />
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

  const player = ranking?.player

  return (
    <div className="animate-fade-in space-y-6">
      <Card className="overflow-hidden">
        <div className="h-24 bg-gradient-to-r from-brand-600 to-blue-600" />
        <div className="px-6 pb-6">
          <div className="-mt-12 mb-4 flex items-end gap-4">
            <div className="flex h-24 w-24 items-center justify-center rounded-2xl border-4 border-surface-900 bg-brand-600/20 text-3xl">
              👤
            </div>
            <div className="mb-1">
              <h2 className="text-2xl font-bold text-white">{player?.full_name || player?.name || 'Pemain'}</h2>
              <p className="text-sm text-gray-400">@{player?.username || 'username'}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <ProfileField label="Nama Lengkap" value={player?.full_name || player?.name || '-'} />
            <ProfileField label="Username ML" value={player?.username || '-'} />
            <ProfileField label="Email" value={session?.email || '-'} />
            <ProfileField label="Role" value={session?.role?.toUpperCase() || '-'} />
          </div>
        </div>
      </Card>

      {player && (
        <Card>
          <h3 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
            <Trophy className="h-5 w-5 text-brand-400" />
            Detail Ranking
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <ProfileField label="Rank Saat Ini" value={player.current_rank || '-'} />
            <ProfileField label="Bintang Rank Saat Ini" value={player.current_stars?.toString() || '-'} />
            <ProfileField label="Rank Tertinggi" value={player.highest_rank || '-'} />
            <ProfileField label="Bintang Rank Tertinggi" value={player.highest_stars?.toString() || '-'} />
            <ProfileField label="Lane #1 Terbaik" value={player.primary_lane || '-'}>
              <span className={`mt-1 inline-block rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.primary_lane] || 'bg-gray-600'}`}>
                {player.primary_lane}
              </span>
            </ProfileField>
            <ProfileField label="Kenyamanan Lane #1" value={`${player.primary_lane_comfort ?? 0}/5`} />
            <ProfileField label="Lane #2 Terbaik" value={player.secondary_lane || '-'}>
              {player.secondary_lane && (
                <span className={`mt-1 inline-block rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.secondary_lane] || 'bg-gray-600'}`}>
                  {player.secondary_lane}
                </span>
              )}
            </ProfileField>
            <ProfileField label="Kenyamanan Lane #2" value={`${player.secondary_lane_comfort ?? 0}/5`} />
          </div>
        </Card>
      )}

      {player && player.skill_score > 0 && (
        <Card>
          <h3 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
            <TrendingUp className="h-5 w-5 text-brand-400" />
            Rincian Skor Individu
          </h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs text-gray-400">Skor Keterampilan</p>
                <p className="text-xs font-bold text-brand-400">Total: {player.skill_score.toFixed(2)}</p>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Rank Saat Ini</span>
                  <span className="text-white">{(player.skill_score_breakdown?.components?.current_rank?.raw_score || 0).toFixed(2)} ({((player.skill_score_breakdown?.components?.current_rank?.raw_score || 0) / (player.skill_score || 1) * 100).toFixed(1)}%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Bintang Rank Saat Ini</span>
                  <span className="text-white">{(player.skill_score_breakdown?.components?.current_star?.raw_score || 0).toFixed(2)} ({((player.skill_score_breakdown?.components?.current_star?.raw_score || 0) / (player.skill_score || 1) * 100).toFixed(1)}%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Rank Tertinggi</span>
                  <span className="text-white">{(player.skill_score_breakdown?.components?.highest_rank?.raw_score || 0).toFixed(2)} ({((player.skill_score_breakdown?.components?.highest_rank?.raw_score || 0) / (player.skill_score || 1) * 100).toFixed(1)}%)</span>
                </div>
                <div className="flex justify-between border-t border-white/10 pt-2">
                  <span className="text-brand-400">Bintang Rank Tertinggi</span>
                  <span className="font-bold text-brand-400">{(player.skill_score_breakdown?.components?.highest_star?.raw_score || 0).toFixed(2)} ({((player.skill_score_breakdown?.components?.highest_star?.raw_score || 0) / (player.skill_score || 1) * 100).toFixed(1)}%)</span>
                </div>
              </div>
            </div>
            <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs text-gray-400">Fleksibilitas Peran</p>
                <p className="text-xs font-bold text-brand-400">Total: {player.role_flexibility_score?.toFixed(1) || '0.0'}%</p>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Kenyamanan Lane Utama</span>
                  <span className="text-white">{player.role_flexibility_breakdown?.primary_comfort || 0}/5 ({player.role_flexibility_breakdown?.normalized_primary?.toFixed?.(1) ?? '0.0'}%)</span>
                </div>
                {player.role_flexibility_breakdown?.secondary_comfort && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Kenyamanan Lane 2</span>
                    <span className="text-white">{player.role_flexibility_breakdown.secondary_comfort}/5</span>
                  </div>
                )}
                <div className="flex justify-between border-t border-white/10 pt-2">
                  <span className="text-brand-400">Kontribusi Lane Utama (70%)</span>
                  <span className="text-white">{((player.role_flexibility_breakdown?.normalized_primary || 0) * 0.7).toFixed(2)}</span>
                </div>
                {player.role_flexibility_breakdown?.secondary_comfort && (
                  <div className="flex justify-between">
                    <span className="text-brand-400">Kontribusi Lane 2 (30%)</span>
                    <span className="text-white">{((5.0 - (player.role_flexibility_breakdown?.secondary_comfort || 0)) / 5.0 * 0.3 * 100).toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between border-t border-white/10 pt-2">
                  <span className="text-brand-400">Skor Fleksibilitas</span>
                  <span className="font-bold text-brand-400">{player.role_flexibility_score?.toFixed?.(1) ?? '0.0'}%</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {ranking && <UserRankingCard rank={ranking.rank} total={ranking.total} player={ranking.player} />}

      <Card>
        <h3 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
          <User className="h-5 w-5 text-brand-400" />
          Tim Saya
        </h3>
        {team?.team_id ? (
          <div className="overflow-x-auto rounded-xl border border-white/5">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-xs uppercase text-gray-400">
                  <th className="px-3 py-3">Pemain</th>
                  <th className="px-3 py-3">Lane Utama</th>
                  <th className="px-3 py-3">Assigned Lane</th>
                  <th className="px-3 py-3 text-center">Peringkat</th>
                  <th className="px-3 py-3 text-center">Bintang</th>
                  <th className="px-3 py-3 text-center">Keterampilan</th>
                  <th className="px-3 py-3 text-center">Kenyamanan</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {team.team.players.map((p: any) => {
                  const primaryComfort = p.primary_lane_comfort ?? 0
                  const secondaryComfort = p.secondary_lane_comfort ?? 0
                  const assignedComfort = p.comfort_in_assigned_lane ?? 0
                  const comfortColor = (v: number) => v <= 2 ? 'text-green-400' : v === 3 ? 'text-amber-400' : 'text-red-400'
                  return (
                    <>
                      <tr key={p.player_id} className={`transition hover:bg-white/5 ${p.is_current_user ? 'bg-brand-500/10' : ''}`}>
                        <td className="px-3 py-3 font-medium text-white">
                          {p.full_name || p.name || p.player_id}
                          {p.is_current_user && <span className="ml-2 text-xs text-brand-400">(Anda)</span>}
                        </td>
                        <td className="px-3 py-3">
                          <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[p.primary_lane] || 'bg-gray-600'}`}>
                            {p.primary_lane}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[p.assigned_lane] || 'bg-gray-600'}`}>
                            {p.assigned_lane}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-center text-gray-300">{p.current_rank}</td>
                        <td className="px-3 py-3 text-center text-gray-300">{p.current_stars}</td>
                        <td className="px-3 py-3 text-center text-gray-300">{p.skill_score?.toFixed(1)}</td>
                        <td className={`px-3 py-3 text-center ${comfortColor(assignedComfort)}`}>{assignedComfort}/5</td>
                      </tr>
                      <tr key={`${p.player_id}-breakdown`}>
                        <td colSpan={7} className="px-3 py-0">
                          <div className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-2">
                            <div className="rounded-xl border border-white/5 bg-surface-900/60 p-3">
                              <h5 className="mb-2 text-xs font-semibold text-white">Transparansi Skor Keterampilan</h5>
                              <div className="space-y-1 text-xs">
                                {p.skill_score_breakdown?.components && Object.entries(p.skill_score_breakdown.components).map(([key, comp]: [string, any]) => (
                                  <div key={key} className="flex flex-col rounded-lg bg-surface-950/60 px-3 py-2">
                                    <div className="flex items-center justify-between">
                                      <span className="text-gray-400">{key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}</span>
                                      <span className="text-xs text-gray-500">Bobot: {(comp.weight_percent ?? 0).toFixed(0)}%</span>
                                    </div>
                                    <div className="mt-1 flex items-center justify-between text-xs">
                                      <span className="text-gray-300">Raw Score: {comp.raw_score?.toFixed?.(2) ?? '-'}</span>
                                      <span className="text-brand-400">Kontribusi: {comp.contribution?.toFixed?.(2) ?? '-'}</span>
                                    </div>
                                    <div className="mt-1 text-[10px] text-gray-500">
                                      {comp.formula}
                                    </div>
                                  </div>
                                ))}
                                {p.skill_score_breakdown?.calculation && (
                                  <div className="mt-2 rounded-lg bg-brand-500/10 px-3 py-2 text-right">
                                    <p className="text-[10px] text-gray-400">Total Skor Keterampilan</p>
                                    <p className="text-sm font-bold text-brand-400">{p.skill_score_breakdown.final_score?.toFixed?.(2) ?? '-'}</p>
                                    <p className="text-[10px] text-gray-500">{p.skill_score_breakdown.calculation}</p>
                                  </div>
                                )}
                              </div>
                            </div>
                            <div className="rounded-xl border border-white/5 bg-surface-900/60 p-3">
                              <h5 className="mb-2 text-xs font-semibold text-white">Transparansi Fleksibilitas Peran</h5>
                              <div className="space-y-1 text-xs">
                                {p.role_flexibility_breakdown?.components && Object.entries(p.role_flexibility_breakdown.components).map(([key, comp]: [string, any]) => (
                                  <div key={key} className="flex flex-col rounded-lg bg-surface-950/60 px-3 py-2">
                                    <div className="flex items-center justify-between">
                                      <span className="text-gray-400">{key === 'primary' ? 'Lane Utama' : 'Lane Sekunder'}</span>
                                      <span className="text-xs text-gray-500">Bobot: {(comp.weight_percent ?? 0).toFixed(0)}%</span>
                                    </div>
                                    <div className="mt-1 flex items-center justify-between text-xs">
                                      <span className="text-gray-300">Kenyamanan: {comp.comfort}/5 ({comp.normalized?.toFixed?.(2)}%)</span>
                                      <span className="text-brand-400">Kontribusi: {comp.contribution?.toFixed?.(2) ?? '-'}</span>
                                    </div>
                                    <div className="mt-1 text-[10px] text-gray-500">
                                      {comp.formula}
                                    </div>
                                  </div>
                                ))}
                                {p.role_flexibility_breakdown?.calculation && (
                                  <div className="mt-2 rounded-lg bg-brand-500/10 px-3 py-2 text-right">
                                    <p className="text-[10px] text-gray-400">Skor Fleksibilitas Peran</p>
                                    <p className="text-sm font-bold text-brand-400">{p.role_flexibility_breakdown.flexibility_score?.toFixed?.(2) ?? '-'}%</p>
                                    <p className="text-[10px] text-gray-500">{p.role_flexibility_breakdown.calculation}</p>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
            <Clock className="h-5 w-5 text-amber-400" />
            <p className="text-sm text-amber-200">{team?.message || 'Tim belum tersedia.'}</p>
          </div>
        )}
      </Card>
    </div>
  )
}

function ProfileField({ label, value, mono, children }: { label: string; value: string; mono?: boolean; children?: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/5 bg-surface-950/60 p-3">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`mt-1 truncate text-sm font-medium text-white ${mono ? 'font-mono' : ''}`}>{value}</p>
      {children}
    </div>
  )
}
