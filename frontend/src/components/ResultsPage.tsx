'use client'

import { useState, useEffect } from 'react'
import { getMyTeam, adminGetTeamVersions, getAllTeams, adminGetTeamVersionDetail, getPaymentStatus } from '@/lib/api'
import { Clock, Users, TrendingUp, AlertTriangle, CheckCircle2 } from 'lucide-react'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import { LANE_COLORS } from '@/lib/constants'
import { useAuthToken, useUserSession } from '@/lib/hooks/useAuth'

export default function ResultsPage({ onBack, isAdmin = false }: { onBack?: () => void; isAdmin?: boolean } = {}) {
  const [userTeam, setUserTeam] = useState<any>(null)
  const [teamVersions, setTeamVersions] = useState<any[]>([])
  const [allTeams, setAllTeams] = useState<any[]>([])
  const [selectedVersion, setSelectedVersion] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [paymentStatus, setPaymentStatus] = useState<any>(null)
  const token = useAuthToken()
  const session = useUserSession()

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true)
        setError(null)

        if (isAdmin && token) {
          const data = await adminGetTeamVersions(token)
          setTeamVersions(data.versions || [])
        } else if (token) {
          const [teamData, allTeamsData, paymentData] = await Promise.all([
            getMyTeam(token).catch(() => null),
            getAllTeams(token).catch(() => ({ teams: [], all_paid: false })),
            getPaymentStatus(token).catch(() => null),
          ])
          setUserTeam(teamData)
          setAllTeams(allTeamsData.teams || [])
          setPaymentStatus(paymentData)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Gagal memuat tim')
      } finally {
        setLoading(false)
      }
    }

    init()
  }, [isAdmin, token])

  const handleViewVersion = async (versionId: string) => {
    try {
      const data = await adminGetTeamVersionDetail(token || '', versionId)
      setSelectedVersion(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal memuat detail versi')
    }
  }

  if (loading) {
    return (
      <Card>
        <LoadingSpinner text="Memuat tim..." />
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

  if (!isAdmin && userTeam?.team_id && paymentStatus?.all_paid) {
    return (
      <div className="animate-fade-in space-y-4">
        {onBack && (
          <button
            onClick={onBack}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-gray-300 transition hover:border-brand-500/40 hover:text-white"
          >
            ← Kembali ke Perankingan
          </button>
        )}

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Tim Saya</h2>
              <p className="text-xs text-gray-400">Tim yang telah Anda ikuti</p>
            </div>
            <span className="font-mono text-sm font-bold text-brand-400">Tim {userTeam.team_id}</span>
          </div>
          <div className="overflow-x-auto rounded-xl border border-white/5">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-xs uppercase text-gray-400">
                  <th className="px-3 py-3">Pemain</th>
                  <th className="px-3 py-3">Lane Utama</th>
                  <th className="px-3 py-3 text-center">Kenya. Lane Utama</th>
                  <th className="px-3 py-3">Lane Sekunder</th>
                  <th className="px-3 py-3 text-center">Kenya. Lane 2</th>
                  <th className="px-3 py-3 text-center">Rank Saat Ini</th>
                  <th className="px-3 py-3 text-center">Bintang</th>
                  <th className="px-3 py-3 text-center">Rank Tertinggi</th>
                  <th className="px-3 py-3 text-center">Bintang</th>
                  <th className="px-3 py-3 text-center">Keterampilan</th>
                  <th className="px-3 py-3 text-center">Kenyamanan</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {userTeam.team.players.map((p: any) => {
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
                        <td className={`px-3 py-3 text-center ${comfortColor(primaryComfort)}`}>{primaryComfort}/5</td>
                        <td className="px-3 py-3">
                          {p.secondary_lane ? (
                            <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[p.secondary_lane] || 'bg-gray-600'}`}>
                              {p.secondary_lane}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">-</span>
                          )}
                        </td>
                        <td className={`px-3 py-3 text-center ${comfortColor(secondaryComfort)}`}>{secondaryComfort}/5</td>
                        <td className="px-3 py-3 text-center text-gray-300">{p.current_rank}</td>
                        <td className="px-3 py-3 text-center text-gray-300">{p.current_stars}</td>
                        <td className="px-3 py-3 text-center text-gray-300">{p.highest_rank}</td>
                        <td className="px-3 py-3 text-center text-gray-300">{p.highest_stars}</td>
                        <td className="px-3 py-3 text-center text-gray-300">{p.skill_score?.toFixed(1)}</td>
                        <td className={`px-3 py-3 text-center ${comfortColor(assignedComfort)}`}>{assignedComfort}/5                        </td>
                      </tr>
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
          <BreakdownPanel team={userTeam.team} />
        </Card>

        <Card>
          <h3 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
            <Users className="h-5 w-5 text-brand-400" />
            Semua Tim
          </h3>
          <div className="space-y-6">
            {allTeams.map((team: any) => {
              const coveredLanes = Array.from(new Set((team.players || []).map((p: any) => p.assigned_lane).filter(Boolean)))
              const missingLanes = (['Jungle', 'EXP Lane', 'Mid Lane', 'Gold Lane', 'Roam'] as const).filter(
                (lane) => !coveredLanes.includes(lane)
              )
              const isMyTeam = team.players?.some((p: any) => p.is_current_user)

              return (
                <div key={team.team_id} className={`animate-slide-up rounded-2xl border p-5 ${isMyTeam ? 'border-brand-500/40 bg-brand-500/5' : 'border-white/10 bg-surface-950/60'}`}>
                  <div className="mb-4 flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-bold text-white">Tim {team.team_id}</h3>
                      <p className="text-xs text-gray-400">
                        {team.players?.length || 0} pemain • Keberadilan {(team.overall_fairness ?? '-')?.toFixed?.(1) ?? '-'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-300">
                      <TrendingUp className="h-4 w-4 text-brand-400" />
                      <span>Skill: {team.average_skill_score?.toFixed(1) ?? '-'}</span>
                    </div>
                  </div>

                  {missingLanes.length > 0 && (
                    <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
                      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-200">
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                        Role / Lane yang Tidak Tercover
                      </div>
                      <p className="text-xs text-amber-100">
                        Tim ini tidak mendapatkan {missingLanes.join(', ')}.
                      </p>
                    </div>
                  )}

                  <div className="overflow-x-auto rounded-xl border border-white/5">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-white/10 bg-white/5 text-xs uppercase text-gray-400">
                          <th className="px-3 py-3">Pemain</th>
                          <th className="px-3 py-3">Lane Utama</th>
                          <th className="px-3 py-3 text-center">Kenya. Lane Utama</th>
                          <th className="px-3 py-3">Lane Sekunder</th>
                          <th className="px-3 py-3 text-center">Kenya. Lane 2</th>
                          <th className="px-3 py-3 text-center">Rank Saat Ini</th>
                          <th className="px-3 py-3 text-center">Bintang</th>
                          <th className="px-3 py-3 text-center">Rank Tertinggi</th>
                          <th className="px-3 py-3 text-center">Bintang</th>
                          <th className="px-3 py-3 text-center">Keterampilan</th>
                          <th className="px-3 py-3 text-center">Kenyamanan</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {(team.players || []).map((player: any) => {
                          const primaryComfort = player.primary_lane_comfort ?? 0
                          const secondaryComfort = player.secondary_lane_comfort ?? 0
                          const assignedComfort = player.comfort_in_assigned_lane ?? 0
                          const comfortColor = (v: number) => v <= 2 ? 'text-green-400' : v === 3 ? 'text-amber-400' : 'text-red-400'
                          return (
                            <>
                              <tr key={player.player_id} className={`transition hover:bg-white/5 ${player.is_current_user ? 'bg-brand-500/10' : ''}`}>
                                <td className="px-3 py-3 font-medium text-white">
                                  {player.full_name || player.name || player.player_id}
                                  {player.is_current_user && <span className="ml-2 text-xs text-brand-400">(Anda)</span>}
                                </td>
                                <td className="px-3 py-3">
                                  <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.primary_lane] || 'bg-gray-600'}`}>
                                    {player.primary_lane}
                                  </span>
                                </td>
                                <td className={`px-3 py-3 text-center ${comfortColor(primaryComfort)}`}>{primaryComfort}/5</td>
                                <td className="px-3 py-3">
                                  {player.secondary_lane ? (
                                    <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.secondary_lane] || 'bg-gray-600'}`}>
                                      {player.secondary_lane}
                                    </span>
                                  ) : (
                                    <span className="text-xs text-gray-500">-</span>
                                  )}
                                </td>
                                <td className={`px-3 py-3 text-center ${comfortColor(secondaryComfort)}`}>{secondaryComfort}/5</td>
                                <td className="px-3 py-3 text-center text-gray-300">{player.current_rank}</td>
                                <td className="px-3 py-3 text-center text-gray-300">{player.current_stars}</td>
                                <td className="px-3 py-3 text-center text-gray-300">{player.highest_rank}</td>
                                <td className="px-3 py-3 text-center text-gray-300">{player.highest_stars}</td>
                                 <td className="px-3 py-3 text-center text-gray-300">{player.skill_score?.toFixed(1)}</td>
                                 <td className={`px-3 py-3 text-center ${comfortColor(assignedComfort)}`}>{assignedComfort}/5</td>
                               </tr>
                             </>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      </div>
    )
  }

  if (!isAdmin && !userTeam?.team_id) {
    const isWaitingPayment = userTeam?.message?.includes('pembayaran') || userTeam?.message?.includes('Pembayaran')
    return (
      <Card>
        <div className="flex items-center gap-3">
          <div className={`rounded-xl p-2.5 ${isWaitingPayment ? 'bg-amber-500/10 text-amber-400' : 'bg-brand-500/10 text-brand-400'}`}>
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Tim Belum Tersedia</h3>
            <p className="text-sm text-gray-400">{userTeam?.message || 'Tim belum tersedia. Silakan selesaikan pembayaran untuk melihat tim.'}</p>
            {Array.isArray(userTeam?.unpaid) && userTeam.unpaid.length > 0 && (
              <ul className="mt-2 list-inside list-disc text-xs text-gray-400">
                {userTeam.unpaid.map((name: string, idx: number) => (
                  <li key={idx}>{name}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </Card>
    )
  }

  if (isAdmin && selectedVersion) {
    return (
      <div className="animate-fade-in space-y-4">
        <button
          onClick={() => { setSelectedVersion(null) }}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-gray-300 transition hover:border-brand-500/40 hover:text-white"
        >
          ← Kembali ke Daftar Versi
        </button>

        <Card>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-white">Detail Tim - {selectedVersion.id}</h2>
            <p className="text-xs text-gray-400">
              Total {selectedVersion.total_teams} tim • {selectedVersion.total_participants} peserta • Keberadilan {selectedVersion.overall_fairness?.toFixed(1) ?? '-'}
            </p>
          </div>
          <div className="space-y-6">
            {selectedVersion.teams?.map((team: any) => (
              <TeamSection key={team.team_id} team={team} />
            ))}
          </div>
        </Card>
      </div>
    )
  }

  if (isAdmin) {
    return (
      <div className="animate-fade-in space-y-4">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Versi Tim</h2>
              <p className="text-xs text-gray-400">Daftar semua tim yang telah digenerate</p>
            </div>
          </div>
          {teamVersions.length === 0 ? (
            <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
              <Clock className="h-5 w-5 text-amber-400" />
              <p className="text-sm text-amber-200">Belum ada tim yang digenerate. Silakan generate tim terlebih dahulu.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {teamVersions.map((version) => (
                <div
                  key={version.id}
                  className="group rounded-xl border border-white/10 bg-surface-950/60 p-5 transition hover:border-brand-500/40 hover:bg-brand-950/20"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs text-gray-400">ID Versi</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        version.status === 'CONFIRMED' ? 'border border-green-500/30 bg-green-500/10 text-green-300' : 'border border-amber-500/30 bg-amber-500/10 text-amber-300'
                      }`}
                    >
                      {version.status}
                    </span>
                  </div>
                  <p className="mb-4 break-all font-mono text-xs text-gray-500">{version.id}</p>
                  <div className="mb-4 grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <p className="text-xs text-gray-400">Total Tim</p>
                      <p className="font-bold text-white">{version.total_teams}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Peserta</p>
                      <p className="font-bold text-white">{version.total_participants}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Keberadilan</p>
                      <p className="font-bold text-brand-400">{version.overall_fairness?.toFixed(1) || '-'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Dibuat</p>
                      <p className="font-bold text-xs text-gray-300">{new Date(version.generated_at).toLocaleString('id-ID')}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleViewVersion(version.id)}
                    className="w-full rounded-xl border border-white/10 bg-surface-900/60 py-2 text-sm font-semibold text-gray-300 transition hover:border-brand-500/40 hover:text-white"
                  >
                    Lihat Detail Tim
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    )
  }

  return null
}

function TeamSection({ team }: { team: any }) {
  const breakdown = team.fairness_breakdown || {}
  const coveredLanes = Array.from(new Set((team.players || []).map((p: any) => p.assigned_lane).filter(Boolean)))
  const missingLanes = (['Jungle', 'EXP Lane', 'Mid Lane', 'Gold Lane', 'Roam'] as const).filter(
    (lane) => !coveredLanes.includes(lane)
  )

  return (
    <div className="animate-slide-up rounded-2xl border border-white/10 bg-surface-950/60 p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-white">Tim {team.team_id}</h3>
          <p className="text-xs text-gray-400">
            {team.players?.length || 0} pemain • Keberadilan {(team.overall_fairness ?? '-')?.toFixed?.(1) ?? '-'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-300">
          <TrendingUp className="h-4 w-4 text-brand-400" />
          <span>Skill: {team.average_skill_score?.toFixed(1) ?? '-'}</span>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-3 gap-2 text-center text-xs md:grid-cols-5">
        <Metric label="Keseimbangan Peran" value={`${breakdown.role_balance ?? '-'}%`} helper={`Bobot ${((breakdown.role_balance_weight ?? 0) * 100).toFixed(0)}%`} />
        <Metric label="Keseimbangan Rank" value={`${breakdown.rank_balance ?? '-'}%`} helper={`Bobot ${((breakdown.rank_balance_weight ?? 0) * 100).toFixed(0)}%`} />
        <Metric label="Keseimbangan Skill" value={`${breakdown.skill_balance ?? '-'}%`} helper={`Bobot ${((breakdown.skill_balance_weight ?? 0) * 100).toFixed(0)}%`} />
        <Metric label="Kenyamanan" value={`${breakdown.comfort_score ?? '-'}%`} helper={`Bobot ${((breakdown.comfort_weight ?? 0) * 100).toFixed(0)}%`} />
        <Metric label="Lane Tercover" value={`${breakdown.lanes_covered ?? '-'}/${breakdown.total_lanes ?? '-'}`} helper={`Avg comfort ${breakdown.avg_comfort ?? '-'}`} />
      </div>

      <div className="mb-4 rounded-xl border border-white/5 bg-surface-900/60 p-4">
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-white">
          <CheckCircle2 className="h-4 w-4 text-green-400" />
          Alasan Pembentukan Tim
        </div>
        <p className="text-xs text-gray-300">
          Tim ini terbentuk dengan mempertimbangkan lane utama dan lane sekunder setiap pemain, serta skor keterampilan
          individu. Setiap tim dirancang agar memiliki cakupan lane yang maksimal dan keseimbangan skill yang adil.
          Penentuan lane coverage menggunakan lane yang sebenarnya diassign pada setiap pemain untuk memastikan kelengkapan peran.
        </p>
      </div>

      {missingLanes.length > 0 && (
        <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-amber-200">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Role / Lane yang Tidak Tercover
          </div>
          <p className="text-xs text-amber-100">
            Tim ini tidak mendapatkan {missingLanes.join(', ')}. Setelah mempertimbangkan lane utama dan lane sekunder
            semua peserta yang lolos kualifikasi, lane ini tetap tidak tercover pada hasil assigned lane tim ini.
            Jika penambahan peserta dengan lane
            {missingLanes.length === 1 ? '' : 'selain'} {missingLanes.join(' atau ')} diperlukan,
            pertimbangkan untuk menambah peserta dengan lane tersebut pada kompetisi selanjutnya.
          </p>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-white/5">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/5 text-xs uppercase text-gray-400">
              <th className="px-3 py-3">Pemain</th>
              <th className="px-3 py-3">Lane Utama</th>
              <th className="px-3 py-3 text-center">Kenya. Lane Utama</th>
              <th className="px-3 py-3">Lane Sekunder</th>
              <th className="px-3 py-3 text-center">Kenya. Lane 2</th>
              <th className="px-3 py-3 text-center">Rank Saat Ini</th>
              <th className="px-3 py-3 text-center">Bintang</th>
              <th className="px-3 py-3 text-center">Rank Tertinggi</th>
              <th className="px-3 py-3 text-center">Bintang</th>
              <th className="px-3 py-3 text-center">Keterampilan</th>
              <th className="px-3 py-3 text-center">Kenyamanan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {(team.players || []).map((player: any) => {
              const primaryComfort = player.primary_lane_comfort ?? 0
              const secondaryComfort = player.secondary_lane_comfort ?? 0
              const assignedComfort = player.comfort_in_assigned_lane ?? 0
              const comfortColor = (v: number) => v <= 2 ? 'text-green-400' : v === 3 ? 'text-amber-400' : 'text-red-400'
              return (
                <>
                  <tr key={player.player_id} className={`transition hover:bg-white/5 ${player.is_current_user ? 'bg-brand-500/10' : ''}`}>
                    <td className="px-3 py-3 font-medium text-white">
                      {player.player_name || player.player_id}
                      {player.is_current_user && <span className="ml-2 text-xs text-brand-400">(Anda)</span>}
                    </td>
                    <td className="px-3 py-3">
                      <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.primary_lane] || 'bg-gray-600'}`}>
                        {player.primary_lane}
                      </span>
                    </td>
                    <td className={`px-3 py-3 text-center ${comfortColor(primaryComfort)}`}>{primaryComfort}/5</td>
                    <td className="px-3 py-3">
                      {player.secondary_lane ? (
                        <span className={`rounded-md px-2 py-0.5 text-xs text-white ${LANE_COLORS[player.secondary_lane] || 'bg-gray-600'}`}>
                          {player.secondary_lane}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-500">-</span>
                      )}
                    </td>
                    <td className={`px-3 py-3 text-center ${comfortColor(secondaryComfort)}`}>{secondaryComfort}/5</td>
                    <td className="px-3 py-3 text-center text-gray-300">{player.current_rank}</td>
                    <td className="px-3 py-3 text-center text-gray-300">{player.current_stars}</td>
                    <td className="px-3 py-3 text-center text-gray-300">{player.highest_rank}</td>
                    <td className="px-3 py-3 text-center text-gray-300">{player.highest_stars}</td>
                    <td className="px-3 py-3 text-center text-gray-300">{player.skill_score?.toFixed(1)}</td>
                    <td className={`px-3 py-3 text-center ${comfortColor(assignedComfort)}`}>{assignedComfort}/5</td>
                  </tr>
                </>
              )
            })}
          </tbody>
        </table>
      </div>
      <BreakdownPanel team={team} />
    </div>
  )
}

function Metric({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="rounded-xl border border-white/5 bg-surface-950/60 p-3">
      <p className="text-[10px] text-gray-400">{label}</p>
      <p className="text-sm font-bold text-white">{value}</p>
      {helper && <p className="text-[10px] text-gray-500">{helper}</p>}
    </div>
  )
}

function BreakdownPanel({ team }: { team: any }) {
  const fb = team?.fairness_breakdown || {}
  const roleBalance = typeof fb.role_balance === 'number' ? fb.role_balance : null
  const rankBalance = typeof fb.rank_balance === 'number' ? fb.rank_balance : null
  const skillBalance = typeof fb.skill_balance === 'number' ? fb.skill_balance : null
  const overallFairness = typeof team?.overall_fairness === 'number' ? team.overall_fairness : null
  const avgSkill = typeof fb.avg_skill === 'number' ? fb.avg_skill : null
  const globalAvgSkill = typeof fb.global_avg_skill === 'number' ? fb.global_avg_skill : null
  const skillDeviation = typeof fb.skill_deviation === 'number' ? fb.skill_deviation : null
  const minSkill = typeof fb.min_skill === 'number' ? fb.min_skill : null
  const maxSkill = typeof fb.max_skill === 'number' ? fb.max_skill : null
  const skillStd = typeof fb.skill_std === 'number' ? fb.skill_std : null
  const rankStd = typeof fb.rank_std === 'number' ? fb.rank_std : null
  const lanesCovered = typeof fb.lanes_covered === 'number' ? fb.lanes_covered : null
  const totalLanes = typeof fb.total_lanes === 'number' ? fb.total_lanes : null
  const coverageRatio = typeof fb.coverage_ratio === 'number' ? fb.coverage_ratio : null

  if (!overallFairness && !skillBalance && !roleBalance) return null

  const fmt = (v: number | null, digits = 2) => (v === null || Number.isNaN(v) ? '-' : v.toFixed(digits))

  const calculatedFairness = roleBalance !== null && rankBalance !== null && skillBalance !== null
    ? roleBalance * 0.40 + rankBalance * 0.20 + skillBalance * 0.40
    : null

  return (
    <div className="mt-4 space-y-4">
      <div className="rounded-xl border border-white/5 bg-surface-900/60 p-4">
        <h4 className="mb-3 text-sm font-semibold text-white">Transparansi Penilaian Keberadilan Tim</h4>
        <div className="space-y-2 text-xs">
          {roleBalance !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Keseimbangan Peran</span>
              <div className="flex items-center gap-3">
                <span className="text-white">{fmt(roleBalance)}</span>
                <span className="text-gray-500">Bobot: 40%</span>
                <span className="text-brand-400">Kontribusi: {fmt(roleBalance * 0.40)}</span>
              </div>
            </div>
          )}
          {rankBalance !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Keseimbangan Rank</span>
              <div className="flex items-center gap-3">
                <span className="text-white">{fmt(rankBalance)}</span>
                <span className="text-gray-500">Bobot: 20%</span>
                <span className="text-brand-400">Kontribusi: {fmt(rankBalance * 0.20)}</span>
              </div>
            </div>
          )}
          {skillBalance !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Keseimbangan Skill</span>
              <div className="flex items-center gap-3">
                <span className="text-white">{fmt(skillBalance)}</span>
                <span className="text-gray-500">Bobot: 40%</span>
                <span className="text-brand-400">Kontribusi: {fmt(skillBalance * 0.40)}</span>
              </div>
            </div>
          )}
          <div className="flex items-center justify-between rounded-lg bg-brand-500/10 px-3 py-2">
            <span className="font-semibold text-brand-300">Keberadilan Tim</span>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-400">
                {roleBalance !== null && rankBalance !== null && skillBalance !== null
                  ? `= ${fmt(roleBalance)}×0.40 + ${fmt(rankBalance)}×0.20 + ${fmt(skillBalance)}×0.40`
                  : '-'}
              </span>
              <span className="font-bold text-brand-400">{fmt(overallFairness)}</span>
            </div>
          </div>
          {calculatedFairness !== null && (
            <p className="text-right text-[10px] text-gray-500">
              Perhitungan: {fmt(roleBalance)} × 0.40 + {fmt(rankBalance)} × 0.20 + {fmt(skillBalance)} × 0.40 = {fmt(calculatedFairness)}
            </p>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-white/5 bg-surface-900/60 p-4">
        <h4 className="mb-3 text-sm font-semibold text-white">Transparansi Penilaian Score Skill Tim</h4>
        <div className="space-y-2 text-xs">
          {avgSkill !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Rata-rata Skill Tim</span>
              <span className="text-white">{fmt(avgSkill)}</span>
            </div>
          )}
          {globalAvgSkill !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Global Rata-rata Skill</span>
              <span className="text-white">{fmt(globalAvgSkill)}</span>
            </div>
          )}
          {skillDeviation !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Deviasi Skill</span>
              <span className="text-white">{fmt(skillDeviation)}</span>
            </div>
          )}
          {skillBalance !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Skor Keseimbangan Skill</span>
              <div className="flex items-center gap-3">
                <span className="text-white">{fmt(skillBalance)}</span>
                <span className="text-gray-500">Bobot: 40%</span>
                <span className="text-brand-400">Kontribusi: {fmt(skillBalance * 0.40)}</span>
              </div>
            </div>
          )}
          {skillStd !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Std Skill</span>
              <span className="text-white">{fmt(skillStd)}</span>
            </div>
          )}
          {rankStd !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Std Rank</span>
              <span className="text-white">{fmt(rankStd)}</span>
            </div>
          )}
          {minSkill !== null && maxSkill !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Rentang Skill</span>
              <span className="text-white">{fmt(minSkill)} - {fmt(maxSkill)}</span>
            </div>
          )}
          {lanesCovered !== null && totalLanes !== null && (
            <div className="flex items-center justify-between rounded-lg bg-surface-950/60 px-3 py-2">
              <span className="text-gray-400">Coverage Ratio</span>
              <span className="text-white">{fmt(coverageRatio)} ({lanesCovered}/{totalLanes})</span>
            </div>
          )}
          {skillDeviation !== null && skillBalance !== null && (
            <p className="text-right text-[10px] text-gray-500">
              Perhitungan: max(0, 100 - {fmt(skillDeviation)} × 3) = {fmt(skillBalance)}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

