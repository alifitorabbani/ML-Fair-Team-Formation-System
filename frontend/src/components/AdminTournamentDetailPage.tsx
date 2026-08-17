'use client'

import { useState, useEffect } from 'react'
import { adminGetTournament, adminUpdateTournament, adminGetTournamentTeams, adminGetAvailableTeams, adminCreateGroup, adminUpdateGroup, adminGetGroups, adminClearGroups, adminAutoAssignGroups, adminGenerateSchedule, adminGetSchedule, adminGetStandings, adminRecalculateStandings, adminOverrideStandings, adminCreateMatch, adminUpdateMatch, adminDeleteMatch, adminSubmitMatchResult, adminConfirmMatchResult, adminGenerateKnockout, adminGetKnockout, adminAdvanceKnockout, adminSetPlacement, adminFinalizeChampion, adminSetBracketQualification, adminGetBracketQualifications, adminClearBracketQualifications } from '@/lib/tournamentApi'
import { useAuthToken } from '@/lib/hooks/useAuth'
import { TournamentResponse } from '@/types'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import { ArrowLeft, Save, Users, Calendar, ClipboardList, GitBranch, Trophy } from 'lucide-react'
import AnimatedBracket from './AnimatedBracket'

type Tab = 'config' | 'groups' | 'schedule' | 'matches' | 'standings' | 'knockout' | 'results'

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
  const [bracketQualifications, setBracketQualifications] = useState<any[]>([])
  const [showCreateGroup, setShowCreateGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  const [creatingGroup, setCreatingGroup] = useState(false)
  const [groupError, setGroupError] = useState<string | null>(null)
  const [scheduleConfig, setScheduleConfig] = useState({
    start_date: '',
    end_date: '',
    match_duration_minutes: 45,
    bo_format: 'BO1',
    min_rest_minutes: 60,
    buffer_minutes: 0,
  })
  const [showScheduleConfig, setShowScheduleConfig] = useState(false)

  const load = async () => {
    if (!token) return
    try {
      const data = await adminGetTournament(token, tournamentId)
      setTournament(data)
      const [g, s, st, k, bq] = await Promise.all([
        adminGetGroups(token, tournamentId),
        adminGetSchedule(token, tournamentId),
        adminGetStandings(token, tournamentId),
        adminGetKnockout(token, tournamentId),
        adminGetBracketQualifications(token, tournamentId),
      ])
      setGroups(g)
      setSchedule(s)
      setStandings(st)
      setKnockout(k)
      setBracketQualifications(bq)
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
      const result = await adminGenerateSchedule(token, tournamentId, {
        start_date: scheduleConfig.start_date || undefined,
        end_date: scheduleConfig.end_date || undefined,
        match_duration_minutes: scheduleConfig.match_duration_minutes,
        bo_format: scheduleConfig.bo_format,
        min_rest_minutes: scheduleConfig.min_rest_minutes,
        buffer_minutes: scheduleConfig.buffer_minutes,
      })
      setMessage(`Jadwal dibuat: ${result.total_matches} match, fairness score: ${result.fairness_score}`)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal generate jadwal')
    } finally {
      setSaving(false)
    }
  }

  const [matchError, setMatchError] = useState<string | null>(null)

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

  const [matchResults, setMatchResults] = useState<Record<string, { score_a: number; score_b: number; kills_a: number; kills_b: number; deaths_a: number; deaths_b: number }>>({})

  const updateMatchResult = (matchId: string, field: string, value: number) => {
    setMatchResults((prev) => ({
      ...prev,
      [matchId]: {
        ...(prev[matchId] || { score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0 }),
        [field]: value,
      },
    }))
  }

  const handleSubmitMatchResult = async (matchId: string) => {
    if (!token) return
    const data = matchResults[matchId]
    if (!data) return
    if (data.score_a === data.score_b) {
      setMatchError('Score tidak boleh sama')
      return
    }
    setSaving(true)
    setMatchError(null)
    try {
      await adminSubmitMatchResult(token, tournamentId, matchId, data)
      setMessage('Hasil pertandingan berhasil disimpan')
      load()
    } catch (err) {
      setMatchError(err instanceof Error ? err.message : 'Gagal menyimpan hasil')
    } finally {
      setSaving(false)
    }
  }

  const handleCreateGroup = async () => {
    if (!token || !newGroupName.trim()) return
    setCreatingGroup(true)
    setGroupError(null)
    try {
      await adminCreateGroup(token, tournamentId, { name: newGroupName.trim(), team_ids: [] })
      setNewGroupName('')
      setShowCreateGroup(false)
      load()
      setMessage('Group berhasil dibuat')
    } catch (err) {
      setGroupError(err instanceof Error ? err.message : 'Gagal membuat group')
    } finally {
      setCreatingGroup(false)
    }
  }

  if (!tournament) {
    if (error) {
      return (
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <ErrorMessage title="Error" message={error} />
          <button onClick={onBack} className="rounded-xl border border-white/10 px-4 py-2 text-sm text-gray-300 hover:text-white">
            Kembali
          </button>
        </div>
      )
    }
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

      {activeTab === 'groups' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-lg font-semibold text-white">Kelola Group</h3>
            <div className="flex flex-wrap gap-2">
              {!showCreateGroup && (
                <button
                  onClick={() => setShowCreateGroup(true)}
                  className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
                >
                  + Buat Group
                </button>
              )}
              {groups.length > 0 && (
                <button
                  onClick={async () => {
                    if (!token) return
                    if (!confirm('Hapus semua group dan isinya?')) return
                    try {
                      await adminClearGroups(token, tournamentId)
                      load()
                    } catch (err) {
                      alert(err instanceof Error ? err.message : 'Gagal mengosongkan group')
                    }
                  }}
                  className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white"
                >
                  Kosongkan Semua Group
                </button>
              )}
              {groups.length > 0 && (
                <button
                  onClick={async () => {
                    if (!token) return
                    try {
                      await adminAutoAssignGroups(token, tournamentId)
                      load()
                    } catch (err) {
                      alert(err instanceof Error ? err.message : 'Gagal mengisi group otomatis')
                    }
                  }}
                  className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
                >
                  Auto-Isi Group
                </button>
              )}
            </div>
          </div>

          {showCreateGroup && (
            <Card>
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-300">Nama Group</label>
                  <input
                    type="text"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateGroup()}
                    className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-brand-500 focus:outline-none"
                    placeholder="Contoh: Group A"
                    autoFocus
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleCreateGroup}
                    disabled={creatingGroup || !newGroupName.trim()}
                    className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
                  >
                    {creatingGroup ? 'Menyimpan...' : 'Buat Group'}
                  </button>
                  <button
                    onClick={() => { setShowCreateGroup(false); setNewGroupName('') }}
                    className="rounded-xl border border-white/10 px-4 py-2 text-sm text-gray-400 hover:text-white"
                  >
                    Batal
                  </button>
                </div>
                {groupError && <p className="text-xs text-red-400">{groupError}</p>}
              </div>
            </Card>
          )}

          {groups.length === 0 ? (
            <Card>
              <p className="text-sm text-gray-400">Belum ada group. Klik "Buat Group" untuk membuat group baru.</p>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {groups.map((group: any) => (
                <GroupCard
                  key={group.id}
                  token={token}
                  tournamentId={tournamentId}
                  group={group}
                  onUpdated={load}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'schedule' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleGenerateSchedule}
              disabled={saving}
              className="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
            >
              <Calendar className="h-4 w-4" />
              Generate Jadwal
            </button>
            <button
              onClick={() => setShowScheduleConfig(!showScheduleConfig)}
              className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white"
            >
              {showScheduleConfig ? 'Sembunyikan Konfigurasi' : 'Konfigurasi Jadwal'}
            </button>
          </div>
          {showScheduleConfig && (
            <Card>
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-300">Tanggal Mulai</label>
                    <input
                      type="date"
                      value={scheduleConfig.start_date}
                      onChange={(e) => setScheduleConfig((prev) => ({ ...prev, start_date: e.target.value }))}
                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-300">Tanggal Selesai</label>
                    <input
                      type="date"
                      value={scheduleConfig.end_date}
                      onChange={(e) => setScheduleConfig((prev) => ({ ...prev, end_date: e.target.value }))}
                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-300">Durasi Match (menit)</label>
                    <input
                      type="number"
                      min={1}
                      value={scheduleConfig.match_duration_minutes}
                      onChange={(e) => setScheduleConfig((prev) => ({ ...prev, match_duration_minutes: parseInt(e.target.value || '45', 10) }))}
                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-300">Format BO</label>
                    <select
                      value={scheduleConfig.bo_format}
                      onChange={(e) => setScheduleConfig((prev) => ({ ...prev, bo_format: e.target.value }))}
                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
                    >
                      <option value="BO1">BO1</option>
                      <option value="BO3">BO3</option>
                      <option value="BO5">BO5</option>
                      <option value="BO7">BO7</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-300">Min Rest (menit)</label>
                    <input
                      type="number"
                      min={0}
                      value={scheduleConfig.min_rest_minutes}
                      onChange={(e) => setScheduleConfig((prev) => ({ ...prev, min_rest_minutes: parseInt(e.target.value || '60', 10) }))}
                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-300">Buffer (menit)</label>
                    <input
                      type="number"
                      min={0}
                      value={scheduleConfig.buffer_minutes}
                      onChange={(e) => setScheduleConfig((prev) => ({ ...prev, buffer_minutes: parseInt(e.target.value || '0', 10) }))}
                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            </Card>
          )}
          {matchError && <p className="text-xs text-red-400">{matchError}</p>}
          {schedule.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada jadwal.</p></Card>
          ) : (
            <div className="space-y-2">
              {schedule.map((m) => {
                const result = matchResults[m.id] || { score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0 }
                const isCompleted = m.status === 'COMPLETED'
                return (
                  <Card key={m.id}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="text-sm font-medium text-white">{m.team_a_id} vs {m.team_b_id}</div>
                        <div className="text-xs text-gray-400">{m.scheduled_date} • {m.start_time} - {m.end_time} • {m.format}</div>
                      </div>
                      <span className={`rounded-full px-2 py-1 text-xs font-medium ${isCompleted ? 'bg-green-500/10 text-green-300' : 'bg-gray-500/10 text-gray-300'}`}>
                        {m.status}
                      </span>
                    </div>
                    {isCompleted && (
                      <div className="mt-2 text-sm font-semibold text-white">
                        {m.score_a} - {m.score_b}
                        {m.winner_team_id && <span className="ml-2 text-green-400">Win: {m.winner_team_id}</span>}
                        <span className="ml-2 text-gray-400">K: {m.kills_a}-{m.kills_b} D: {m.deaths_a}-{m.deaths_b}</span>
                      </div>
                    )}
                    {!isCompleted && (
                      <div className="mt-3 space-y-2">
                        <div className="grid gap-2 md:grid-cols-2">
                          <div>
                            <label className="mb-1 block text-xs text-gray-400">Score {m.team_a_id}</label>
                            <input
                              type="number"
                              min={0}
                              value={result.score_a}
                              onChange={(e) => updateMatchResult(m.id, 'score_a', parseInt(e.target.value || '0', 10))}
                              className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs text-gray-400">Score {m.team_b_id}</label>
                            <input
                              type="number"
                              min={0}
                              value={result.score_b}
                              onChange={(e) => updateMatchResult(m.id, 'score_b', parseInt(e.target.value || '0', 10))}
                              className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs text-gray-400">Kills {m.team_a_id}</label>
                            <input
                              type="number"
                              min={0}
                              value={result.kills_a}
                              onChange={(e) => updateMatchResult(m.id, 'kills_a', parseInt(e.target.value || '0', 10))}
                              className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs text-gray-400">Kills {m.team_b_id}</label>
                            <input
                              type="number"
                              min={0}
                              value={result.kills_b}
                              onChange={(e) => updateMatchResult(m.id, 'kills_b', parseInt(e.target.value || '0', 10))}
                              className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs text-gray-400">Deaths {m.team_a_id}</label>
                            <input
                              type="number"
                              min={0}
                              value={result.deaths_a}
                              onChange={(e) => updateMatchResult(m.id, 'deaths_a', parseInt(e.target.value || '0', 10))}
                              className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-xs text-gray-400">Deaths {m.team_b_id}</label>
                            <input
                              type="number"
                              min={0}
                              value={result.deaths_b}
                              onChange={(e) => updateMatchResult(m.id, 'deaths_b', parseInt(e.target.value || '0', 10))}
                              className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                            />
                          </div>
                        </div>
                        <button
                          onClick={() => handleSubmitMatchResult(m.id)}
                          disabled={saving}
                          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
                        >
                          {saving ? 'Menyimpan...' : 'Simpan Hasil'}
                        </button>
                      </div>
                    )}
                  </Card>
                )
              })}
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
          <div className="flex flex-wrap gap-2">
            <button onClick={handleRecalculateStandings} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500">
              Hitung Ulang Klasemen
            </button>
            <button
              onClick={async () => {
                if (!token) return
                if (!confirm('Hapus semua kualifikasi bracket?')) return
                try {
                  await adminClearBracketQualifications(token, tournamentId)
                  setBracketQualifications([])
                  setMessage('Kualifikasi bracket dihapus')
                } catch (err) {
                  alert(err instanceof Error ? err.message : 'Gagal menghapus kualifikasi bracket')
                }
              }}
              className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white"
            >
              Reset Kualifikasi Bracket
            </button>
          </div>
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
                      <th className="pb-2 pr-4">WR</th>
                      <th className="pb-2 pr-4">Bracket</th>
                      <th className="pb-2">Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.standings.map((s: any) => {
                      const winRate = s.played > 0 ? ((s.win / s.played) * 100).toFixed(1) : '0.0'
                      const qualification = bracketQualifications.find((q: any) => q.team_id === s.team_id)
                      const isEliminated = !qualification || !qualification.bracket_type
                      const bracketColors: Record<string, string> = {
                        UPPER: 'bg-green-500/10 text-green-300',
                        LOWER: 'bg-yellow-500/10 text-yellow-300',
                      }
                      const bracketLabels: Record<string, string> = {
                        UPPER: 'Upper',
                        LOWER: 'Lower',
                      }
                      return (
                        <tr key={s.team_id} className={`border-b ${isEliminated ? 'bg-red-500/5' : 'border-white/5'}`}>
                          <td className="py-2 pr-4 text-gray-300">{s.rank || '-'}</td>
                          <td className={`py-2 pr-4 ${isEliminated ? 'text-red-300' : 'text-white'}`}>{s.team_name || s.team_id}</td>
                          <td className="py-2 pr-4 text-gray-300">{s.played}</td>
                          <td className="py-2 pr-4 text-green-400">{s.win}</td>
                          <td className="py-2 pr-4 text-red-400">{s.loss}</td>
                          <td className="py-2 pr-4 text-gray-300">{s.kill}</td>
                          <td className="py-2 pr-4 text-gray-300">{s.death}</td>
                          <td className="py-2 pr-4 text-gray-300">{s.kill_difference > 0 ? '+' : ''}{s.kill_difference}</td>
                          <td className="py-2 pr-4 text-gray-300">{winRate}%</td>
                          <td className="py-2 pr-4">
                            <select
                              value={qualification?.bracket_type || ''}
                              onChange={async (e) => {
                                const bracketType = e.target.value
                                if (!bracketType) return
                                try {
                                  await adminSetBracketQualification(token, tournamentId, {
                                    team_id: s.team_id,
                                    bracket_type: bracketType,
                                    group_id: group.group_id,
                                    rank: s.rank,
                                  })
                                  const updated = await adminGetBracketQualifications(token, tournamentId)
                                  setBracketQualifications(updated)
                                  setMessage('Kualifikasi bracket disimpan')
                                } catch (err) {
                                  alert(err instanceof Error ? err.message : 'Gagal menyimpan kualifikasi bracket')
                                }
                              }}
                              className="rounded-xl border border-white/10 bg-surface-900/60 px-2 py-1 text-xs text-white focus:border-brand-500 focus:outline-none"
                            >
                              <option value="">-</option>
                              <option value="UPPER">Upper</option>
                              <option value="LOWER">Lower</option>
                            </select>
                          </td>
                          <td className="py-2 font-semibold text-white">{s.points}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          ))}
        </div>
      )}

      {activeTab === 'knockout' && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
          <button
            onClick={async () => {
              if (!token) return
              try {
                const qualified = standings.flatMap((group: any) => 
                  group.standings
                    .filter((s: any) => s.rank <= 8)
                    .map((s: any) => s.team_id)
                )
                if (qualified.length === 0) {
                  alert('Tidak ada tim yang lolos kualifikasi')
                  return
                }
                const upperTeams = qualified.slice(0, 4)
                const lowerTeams = qualified.slice(4, 8)
                if (upperTeams.length >= 2) {
                  await adminGenerateKnockout(token, tournamentId, 'UPPER', upperTeams, false)
                }
                if (lowerTeams.length >= 2) {
                  await adminGenerateKnockout(token, tournamentId, 'LOWER', lowerTeams, false)
                }
                load()
              } catch (err) {
                alert(err instanceof Error ? err.message : 'Gagal generate bracket')
              }
            }}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
          >
            Generate Bracket
          </button>
          <button
            onClick={async () => {
              if (!token) return
              try {
                const qualified = standings.flatMap((group: any) => 
                  group.standings
                    .filter((s: any) => s.rank <= 8)
                    .map((s: any) => s.team_id)
                )
                if (qualified.length === 0) {
                  alert('Tidak ada tim yang lolos kualifikasi')
                  return
                }
                const upperTeams = qualified.slice(0, 4)
                const lowerTeams = qualified.slice(4, 8)
                if (upperTeams.length >= 2) {
                  await adminGenerateKnockout(token, tournamentId, 'UPPER', upperTeams, true)
                }
                if (lowerTeams.length >= 2) {
                  await adminGenerateKnockout(token, tournamentId, 'LOWER', lowerTeams, true)
                }
                load()
              } catch (err) {
                alert(err instanceof Error ? err.message : 'Gagal finalize bracket')
              }
            }}
            className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white"
          >
            Finalize Bracket
          </button>
            <button
              onClick={async () => {
                if (!token) return
                await adminClearBracketQualifications(token, tournamentId)
                setBracketQualifications([])
                setMessage('Kualifikasi bracket dihapus')
                load()
              }}
              className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white"
            >
              Reset Kualifikasi
            </button>
          </div>
          {knockout.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada bracket.</p></Card>
          ) : (
            <AnimatedBracket
              upperMatches={knockout.filter((b: any) => b.bracket_type === 'UPPER').flatMap((b: any) => b.rounds?.flatMap((r: any) => r.slots?.map((s: any) => ({ ...s, bracket_type: 'UPPER' as const })) || [])).filter((m: any) => m.team_id)}
              lowerMatches={knockout.filter((b: any) => b.bracket_type === 'LOWER').flatMap((b: any) => b.rounds?.flatMap((r: any) => r.slots?.map((s: any) => ({ ...s, bracket_type: 'LOWER' as const })) || [])).filter((m: any) => m.team_id)}
              grandFinal={null}
              token={token}
              tournamentId={tournamentId}
              onMatchUpdate={load}
            />
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

function GroupCard({ token, tournamentId, group, onUpdated }: { token: string | null; tournamentId: string; group: any; onUpdated: () => void }) {
  const [editing, setEditing] = useState(false)
  const [availableTeams, setAvailableTeams] = useState<any[]>([])
  const [selectedTeamIds, setSelectedTeamIds] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [standings, setStandings] = useState<any[]>([])
  const [loadingStandings, setLoadingStandings] = useState(false)

  const loadAvailable = async () => {
    if (!token) return
    try {
      const teams = await adminGetAvailableTeams(token, tournamentId)
      setAvailableTeams(teams)
    } catch {
      // ignore
    }
  }

  const loadStandings = async () => {
    if (!token) return
    setLoadingStandings(true)
    try {
      const data = await adminGetStandings(token, tournamentId)
      const groupStandings = data.find((g: any) => g.group_id === group.id)
      setStandings(groupStandings?.standings || [])
    } catch {
      // ignore
    } finally {
      setLoadingStandings(false)
    }
  }

  useEffect(() => {
    loadStandings()
  }, [token, tournamentId, group.id])

  useEffect(() => {
    if (editing) {
      loadAvailable()
    }
  }, [editing])

  useEffect(() => {
    if (group.members?.length > 0) {
      loadStandings()
    }
  }, [group.members])

  const handleSave = async () => {
    if (!token) return
    setSaving(true)
    try {
                      const currentIds = (group.members || []).map((m: any) => m.team_id).filter(Boolean)
                      const newIds = Array.from(new Set([...currentIds, ...selectedTeamIds]))
      await adminUpdateGroup(token, tournamentId, group.id, { team_ids: newIds })
      setEditing(false)
      onUpdated()
      loadStandings()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Gagal menyimpan group')
    } finally {
      setSaving(false)
    }
  }

  const handleRemove = async (teamId: string) => {
    if (!token) return
    const currentIds = (group.members || []).map((m: any) => m.team_id).filter(Boolean).filter((id: string) => id !== teamId)
    try {
      await adminUpdateGroup(token, tournamentId, group.id, { team_ids: currentIds })
      onUpdated()
      loadStandings()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Gagal menghapus tim dari group')
    }
  }

  const assignedCount = group.members?.length || 0

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h4 className="text-base font-semibold text-white">{group.name}</h4>
          <p className="text-xs text-gray-400">{assignedCount} tim</p>
        </div>
        {assignedCount > 0 && (
          <button
            onClick={() => setEditing(!editing)}
            className="rounded-xl border border-white/10 px-3 py-1.5 text-xs font-medium text-gray-300 hover:text-white"
          >
            {editing ? 'Batal' : 'Edit'}
          </button>
        )}
      </div>

      {!editing ? (
        <div className="space-y-3">
          {assignedCount === 0 ? (
            <p className="text-xs text-gray-500">Belum ada tim. Gunakan tombol Auto-Isi Group untuk mengisi group ini.</p>
          ) : (
            <div className="space-y-2">
              {group.members.map((m: any) => (
                <div key={m.id} className="flex items-center justify-between rounded-xl border border-white/5 bg-surface-900/40 px-3 py-2">
                  <div>
                    <div className="text-sm text-white">{m.team_name_snapshot || m.team_id}</div>
                    <div className="text-xs text-gray-500">Seed: {m.seed || '-'}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {standings.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs text-gray-400">
                    <th className="pb-1 pr-2">#</th>
                    <th className="pb-1 pr-2">Tim</th>
                    <th className="pb-1 pr-2">P</th>
                    <th className="pb-1 pr-2">W</th>
                    <th className="pb-1 pr-2">L</th>
                    <th className="pb-1 pr-2">K</th>
                    <th className="pb-1 pr-2">D</th>
                    <th className="pb-1 pr-2">KD</th>
                    <th className="pb-1 pr-2">WR</th>
                    <th className="pb-1">Pts</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.map((s: any) => {
                    const winRate = s.played > 0 ? ((s.win / s.played) * 100).toFixed(1) : '0.0'
                    return (
                      <tr key={s.team_id} className="border-b border-white/5">
                        <td className="py-1 pr-2 text-gray-300">{s.rank || '-'}</td>
                        <td className="py-1 pr-2 text-white">{s.team_name || s.team_id}</td>
                        <td className="py-1 pr-2 text-gray-300">{s.played}</td>
                        <td className="py-1 pr-2 text-green-400">{s.win}</td>
                        <td className="py-1 pr-2 text-red-400">{s.loss}</td>
                        <td className="py-1 pr-2 text-gray-300">{s.kill}</td>
                        <td className="py-1 pr-2 text-gray-300">{s.death}</td>
                        <td className="py-1 pr-2 text-gray-300">{s.kill_difference > 0 ? '+' : ''}{s.kill_difference}</td>
                        <td className="py-1 pr-2 text-gray-300">{winRate}%</td>
                        <td className="py-1 font-semibold text-white">{s.points}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
          {loadingStandings && <p className="text-xs text-gray-500">Memuat klasemen...</p>}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-300">Tersedia untuk ditambahkan:</p>
            {availableTeams.length === 0 ? (
              <p className="text-xs text-gray-500">Semua tim sudah masuk group.</p>
            ) : (
              <div className="max-h-40 space-y-1 overflow-y-auto">
                {availableTeams.map((t: any) => (
                  <label key={t.id} className="flex items-center gap-2 rounded-xl border border-white/5 bg-surface-900/40 px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selectedTeamIds.includes(t.team_id)}
                      onChange={(e) => {
                        setSelectedTeamIds((prev) =>
                          e.target.checked ? [...prev, t.team_id] : prev.filter((id: string) => id !== t.team_id)
                        )
                      }}
                      className="h-4 w-4 rounded border-white/20 bg-surface-900/60 text-brand-500 focus:ring-brand-500"
                    />
                    <span className="text-sm text-white">{t.team_name_snapshot || t.team_id}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving || selectedTeamIds.length === 0}
              className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
            >
              {saving ? 'Menyimpan...' : 'Tambah Tim'}
            </button>
            <button
              onClick={() => {
                setEditing(false)
                setSelectedTeamIds([])
              }}
              className="rounded-xl border border-white/10 px-4 py-2 text-sm text-gray-400 hover:text-white"
            >
              Batal
            </button>
          </div>
        </div>
      )}
    </Card>
  )
}
