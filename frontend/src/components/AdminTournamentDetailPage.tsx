'use client'

import { useState, useEffect } from 'react'
import { adminGetTournament, adminUpdateTournament, adminSelectTeams, adminCreateGroup, adminUpdateGroup, adminGenerateSchedule, adminGetSchedule, adminGetStandings, adminRecalculateStandings, adminOverrideStandings, adminCreateMatch, adminUpdateMatch, adminDeleteMatch, adminSubmitMatchResult, adminConfirmMatchResult, adminGenerateKnockout, adminGetKnockout, adminAdvanceKnockout, adminSetPlacement, adminFinalizeChampion } from '@/lib/tournamentApi'
import { useAuthToken } from '@/lib/hooks/useAuth'
import { TournamentResponse } from '@/types'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import { ArrowLeft, Save, Users, Calendar, ClipboardList, GitBranch, Trophy } from 'lucide-react'

type Tab = 'config' | 'groups' | 'schedule' | 'matches' | 'knockout' | 'results'

export default function AdminTournamentDetailPage({ tournamentId, onBack }: { tournamentId: string; onBack: () => void }) {
  const token = useAuthToken()
  const [tournament, setTournament] = useState<TournamentResponse | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('config')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [groups, setGroups] = useState<any[]>([])
  const [schedule, setSchedule] = useState<any[]>([])
  const [standings, setStandings] = useState<any[]>([])
  const [knockout, setKnockout] = useState<any[]>([])
  const [matches, setMatches] = useState<any[]>([])

  const load = async () => {
    if (!token) return
    try {
      const data = await adminGetTournament(token, tournamentId)
      setTournament(data)
      const [s, st, k] = await Promise.all([
        adminGetSchedule(token, tournamentId),
        adminGetStandings(token, tournamentId),
        adminGetKnockout(token, tournamentId),
      ])
      setSchedule(s)
      setStandings(st)
      setKnockout(k)
      const m = await adminGetSchedule(token, tournamentId)
      setMatches(m)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal memuat data')
    }
  }

  useEffect(() => {
    load()
  }, [token, tournamentId])

  const handleUpdate = async (data: any) => {
    if (!token) return
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const updated = await adminUpdateTournament(token, tournamentId, data)
      setTournament(updated)
      setMessage('Berhasil disimpan')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal menyimpan')
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateSchedule = async () => {
    if (!token) return
    setSaving(true)
    setError(null)
    try {
      const result = await adminGenerateSchedule(token, tournamentId)
      setMessage(`Jadwal dibuat: ${result.total_matches} match, fairness score: ${result.fairness_score}`)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal generate jadwal')
    } finally {
      setSaving(false)
    }
  }

  const handleRecalculateStandings = async () => {
    if (!token) return
    setSaving(true)
    try {
      await adminRecalculateStandings(token, tournamentId)
      setMessage('Klasemen berhasil dihitung ulang')
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal menghitung ulang')
    } finally {
      setSaving(false)
    }
  }

  if (!tournament) {
    return <div className="flex items-center justify-center py-20"><LoadingSpinner text="Memuat..." /></div>
  }

  const tabs: { key: Tab; label: string; icon: any }[] = [
    { key: 'config', label: 'Konfigurasi', icon: Trophy },
    { key: 'groups', label: 'Group', icon: Users },
    { key: 'schedule', label: 'Jadwal', icon: Calendar },
    { key: 'matches', label: 'Match', icon: ClipboardList },
    { key: 'knockout', label: 'Knockout', icon: GitBranch },
    { key: 'results', label: 'Hasil', icon: ClipboardList },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="text-sm text-gray-400 hover:text-white">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h2 className="text-2xl font-bold text-white">{tournament.name}</h2>
          <p className="mt-1 text-sm text-gray-400">Status: {tournament.status}</p>
        </div>
      </div>

      {message && <div className="rounded-xl bg-green-500/10 px-4 py-2 text-sm text-green-300">{message}</div>}
      {error && <ErrorMessage title="Error" message={error} />}

      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.key
                ? 'brand-gradient text-white shadow-brand'
                : 'border border-white/10 bg-surface-900/60 text-gray-400 hover:text-white'
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'config' && (
        <Card>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-300">Nama</label>
              <input
                type="text"
                defaultValue={tournament.name}
                onBlur={(e) => handleUpdate({ name: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-300">Deskripsi</label>
              <textarea
                defaultValue={tournament.description || ''}
                onBlur={(e) => handleUpdate({ description: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
                rows={3}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-300">Timezone</label>
              <input
                type="text"
                defaultValue={tournament.timezone}
                onBlur={(e) => handleUpdate({ timezone: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-300">Third Place Mode</label>
              <select
                defaultValue={tournament.third_place_mode}
                onChange={(e) => handleUpdate({ third_place_mode: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="DISABLED">Disabled</option>
                <option value="THIRD_PLACE_MATCH">Third Place Match</option>
                <option value="BRACKET_BASED">Bracket Based</option>
                <option value="MANUAL">Manual</option>
              </select>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'schedule' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <button
              onClick={handleGenerateSchedule}
              disabled={saving}
              className="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
            >
              <Calendar className="h-4 w-4" />
              Generate Jadwal
            </button>
          </div>
          {schedule.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada jadwal.</p></Card>
          ) : (
            <div className="space-y-2">
              {schedule.map((m) => (
                <Card key={m.id}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium text-white">{m.team_a_id} vs {m.team_b_id}</div>
                      <div className="text-xs text-gray-400">{m.scheduled_date} • {m.start_time} - {m.end_time}</div>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${m.status === 'COMPLETED' ? 'bg-green-500/10 text-green-300' : 'bg-gray-500/10 text-gray-300'}`}>
                      {m.status}
                    </span>
                  </div>
                  {m.status === 'COMPLETED' && (
                    <div className="mt-2 text-sm font-semibold text-white">
                      {m.score_a} - {m.score_b}
                      {m.winner_team_id && <span className="ml-2 text-green-400">Win</span>}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'matches' && (
        <div className="space-y-4">
          {matches.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada match.</p></Card>
          ) : (
            matches.map((m) => (
              <Card key={m.id}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium text-white">{m.team_a_id} vs {m.team_b_id}</div>
                    <div className="text-xs text-gray-400">{m.stage} • {m.scheduled_date} • {m.format}</div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${m.status === 'COMPLETED' ? 'bg-green-500/10 text-green-300' : 'bg-gray-500/10 text-gray-300'}`}>
                    {m.status}
                  </span>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'standings' && (
        <div className="space-y-4">
          <button onClick={handleRecalculateStandings} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500">
            Hitung Ulang Klasemen
          </button>
          {standings.map((group) => (
            <Card key={group.group_id}>
              <h3 className="mb-3 text-lg font-semibold text-white">{group.group_name}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs text-gray-400">
                      <th className="pb-2 pr-4">#</th>
                      <th className="pb-2 pr-4">Tim</th>
                      <th className="pb-2 pr-4">P</th>
                      <th className="pb-2 pr-4">W</th>
                      <th className="pb-2 pr-4">L</th>
                      <th className="pb-2 pr-4">K</th>
                      <th className="pb-2 pr-4">D</th>
                      <th className="pb-2 pr-4">KD</th>
                      <th className="pb-2">Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.standings.map((s: any) => (
                      <tr key={s.team_id} className="border-b border-white/5">
                        <td className="py-2 pr-4 text-gray-300">{s.rank || '-'}</td>
                        <td className="py-2 pr-4 text-white">{s.team_name || s.team_id}</td>
                        <td className="py-2 pr-4 text-gray-300">{s.played}</td>
                        <td className="py-2 pr-4 text-green-400">{s.win}</td>
                        <td className="py-2 pr-4 text-red-400">{s.loss}</td>
                        <td className="py-2 pr-4 text-gray-300">{s.kill}</td>
                        <td className="py-2 pr-4 text-gray-300">{s.death}</td>
                        <td className="py-2 pr-4 text-gray-300">{s.kill_difference > 0 ? '+' : ''}{s.kill_difference}</td>
                        <td className="py-2 font-semibold text-white">{s.points}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ))}
        </div>
      )}

      {activeTab === 'knockout' && (
        <div className="space-y-6">
          <button
            onClick={async () => {
              if (!token) return
              const qualified = matches.filter(m => m.status === 'COMPLETED').map(m => m.winner_team_id).filter(Boolean) as string[]
              if (qualified.length === 0) return
              await adminGenerateKnockout(token, tournamentId, 'UPPER', qualified)
              load()
            }}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
          >
            Generate Bracket
          </button>
          {knockout.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada bracket.</p></Card>
          ) : (
            knockout.map((bracket) => (
              <Card key={bracket.id}>
                <h3 className="mb-4 text-lg font-semibold text-white">{bracket.name}</h3>
                <div className="space-y-4">
                  {bracket.rounds?.map((round: any) => (
                    <div key={round.id}>
                      <div className="mb-2 text-sm font-medium text-gray-400">{round.round_name}</div>
                      <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
                        {round.slots.map((slot: any) => (
                          <div key={slot.id} className={`rounded-xl border p-3 ${slot.team_id ? 'border-white/10 bg-surface-900/60' : 'border-dashed border-white/5 bg-surface-900/20'}`}>
                            <div className="text-xs text-gray-500">Slot {slot.slot_number}</div>
                            <div className={`mt-1 text-sm ${slot.team_id ? 'text-white' : 'text-gray-600'}`}>
                              {slot.team_id || 'TBD'}
                            </div>
                            <div className={`mt-1 text-xs ${slot.status === 'FILLED' ? 'text-green-400' : 'text-gray-500'}`}>
                              {slot.status}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'results' && (
        <div className="space-y-4">
          {matches.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada hasil.</p></Card>
          ) : (
            matches.filter(m => m.status === 'COMPLETED').map((m) => (
              <Card key={m.id}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium text-white">{m.team_a_id} vs {m.team_b_id}</div>
                    <div className="text-xs text-gray-400">{m.stage} • {m.scheduled_date}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${m.winner_team_id === m.team_a_id ? 'bg-green-500/10 text-green-300' : 'bg-gray-500/10 text-gray-300'}`}>
                      {m.score_a} - {m.score_b}
                    </span>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  )
}
