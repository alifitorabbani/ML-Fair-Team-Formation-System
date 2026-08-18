'use client'

import { useState, useEffect } from 'react'
import { adminUpdateTournament, adminGetTournamentTeams, adminGetAvailableTeams, adminCreateGroup, adminUpdateGroup, adminGetGroups, adminClearGroups, adminAutoAssignGroups, adminGenerateSchedule, adminGetSchedule, adminGetStandings, adminRecalculateStandings, adminOverrideStandings, adminCreateMatch, adminUpdateMatch, adminDeleteMatch, adminSubmitMatchResult, adminSubmitGameResult, adminConfirmMatchResult, adminGenerateKnockout, adminGetKnockout, adminAdvanceKnockout, adminSetPlacement, adminFinalizeChampion, adminSetBracketQualification, adminGetBracketQualifications, adminClearBracketQualifications, adminResetBracket, adminResolveKnockout, adminGetDailyStandings } from '@/lib/tournamentApi'
import { useAuthToken } from '@/lib/hooks/useAuth'
import { TournamentResponse } from '@/types'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import { ArrowLeft, Save, Users, Calendar, ClipboardList, GitBranch, Trophy } from 'lucide-react'
import AnimatedBracket from './AnimatedBracket'

type Tab = 'config' | 'groups' | 'schedule' | 'matches' | 'standings' | 'knockout' | 'results'

function groupScheduleByStage(matches: any[]): Record<string, any[]> {
  return matches.reduce<Record<string, any[]>>((acc, m) => {
    const stage = m.stage || 'GROUP_STAGE'
    if (!acc[stage]) acc[stage] = []
    acc[stage].push(m)
    return acc
  }, {})
}

export default function AdminTournamentDetailPage({ tournament, onBack }: { tournament: TournamentResponse; onBack: () => void }) {
  const token = useAuthToken()
  const tournamentId = tournament.id
  const [tournamentData, setTournamentData] = useState<TournamentResponse | null>(tournament)
  const [activeTab, setActiveTab] = useState<Tab>('config')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [groups, setGroups] = useState<any[]>([])
  const [schedule, setSchedule] = useState<any[]>([])
  const [standings, setStandings] = useState<any[]>([])
  const [knockout, setKnockout] = useState<{ upper_matches: any[]; lower_matches: any[]; grand_final: any; lower_final: any } | null>(null)
  const [matches, setMatches] = useState<any[]>([])
  const [bracketQualifications, setBracketQualifications] = useState<any[]>([])
  const [dailyStandings, setDailyStandings] = useState<any[]>([])
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [teams, setTeams] = useState<Record<string, string>>({})
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
  const [bracketResolved, setBracketResolved] = useState(false)

  const load = async () => {
    if (!token) return
    try {
      setTournamentData(tournament)
      const [g, s, st, k, bq, t] = await Promise.all([
        adminGetGroups(token, tournament.id),
        adminGetSchedule(token, tournament.id),
        adminGetStandings(token, tournament.id),
        adminGetKnockout(token, tournament.id),
        adminGetBracketQualifications(token, tournament.id),
        adminGetTournamentTeams(token, tournament.id),
      ])
      const teamMap: Record<string, string> = {}
      t.forEach((team: any) => {
        if (team.team_id) {
          teamMap[team.team_id] = team.team_name_snapshot || team.team_id
        }
      })
      setTeams(teamMap)
      setGroups(g)
      setSchedule(s)
      setStandings(st)
      setKnockout(k)
      setBracketQualifications(bq)
      setMatches(s)
      // Auto-resolve bracket when group stage is complete (all teams played = 8)
      const groupMatches = s.filter((m: any) => m.stage === 'GROUP_STAGE')
      const allTeamsPlayedEight = t.length > 0 && groupMatches.length > 0 && t.every((team: any) => {
        const played = groupMatches.filter((m: any) => m.team_a_id === team.team_id || m.team_b_id === team.team_id).length
        return played >= 8
      })
      const hasUnresolvedBracket = k && (k.upper_matches || []).some((m: any) => !m.team_a_id || !m.team_b_id)
      if (allTeamsPlayedEight && hasUnresolvedBracket && !bracketResolved) {
        try {
          await adminResolveKnockout(token, tournament.id)
          setBracketResolved(true)
        } catch {
          // ignore auto-resolve error
        }
        load()
        return
      }
      if (!allTeamsPlayedEight) {
        setBracketResolved(false)
      }
      // Load daily standings for the first available date
      const dates = Array.from(new Set(s.map((match: any) => match.scheduled_date).filter(Boolean)))
      if (dates.length > 0) {
        const firstDate = dates[0]
        setSelectedDate(firstDate)
        try {
          const daily = await adminGetDailyStandings(token, tournamentId, firstDate)
          setDailyStandings(daily.standings || [])
        } catch {
          // ignore daily standings load error
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal memuat data')
    }
  }

  const loadDailyStandings = async (date: string) => {
    if (!token) return
    try {
      const daily = await adminGetDailyStandings(token, tournamentId, date)
      setDailyStandings(daily.standings || [])
    } catch {
      setDailyStandings([])
    }
  }

  const getTeamName = (teamId: string | null | undefined) => {
    if (!teamId) return 'TBD'
    return teams[teamId] || teamId
  }

  useEffect(() => {
    if (selectedDate) {
      loadDailyStandings(selectedDate)
    }
  }, [selectedDate, token, tournamentId])

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
      setTournamentData(updated)
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

  const [matchResults, setMatchResults] = useState<Record<string, { score_a: number; score_b: number; kills_a: number; kills_b: number; deaths_a: number; deaths_b: number; winner_team_id?: string; loser_team_id?: string }>>({})
  const [bracketMapResults, setBracketMapResults] = useState<Record<string, Array<{ map_number: number; winner_team_id?: string }>>>({})
  const [gameResults, setGameResults] = useState<Record<string, Array<{ game_number: number; score_a: number; score_b: number; kills_a: number; kills_b: number; deaths_a: number; deaths_b: number; winner_team_id?: string; scheduled_date?: string; start_time?: string; end_time?: string }>>>({})

  const updateMatchResult = (matchId: string, field: string, value: number | string) => {
    setMatchResults((prev) => ({
      ...prev,
      [matchId]: {
        ...(prev[matchId] || { score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0 }),
        [field]: value,
      },
    }))
  }

  const updateBracketMapResult = (matchId: string, mapNumber: number, winnerTeamId: string) => {
    setBracketMapResults((prev) => {
      const current = prev[matchId] || []
      const existing = current.find((m) => m.map_number === mapNumber)
      if (existing) {
        return {
          ...prev,
          [matchId]: current.map((m) => m.map_number === mapNumber ? { ...m, winner_team_id: winnerTeamId } : m),
        }
      }
      return {
        ...prev,
        [matchId]: [...current, { map_number: mapNumber, winner_team_id: winnerTeamId }],
      }
    })
  }

  const handleSubmitGameResult = async (matchId: string, gameIndex: number, matchFormat: string) => {
    if (!token) return
    const gamesData = gameResults[matchId] || []
    const gameResult = gamesData[gameIndex]
    if (!gameResult) return
    
    setSaving(true)
    setMatchError(null)
    try {
      await adminSubmitGameResult(token, tournamentId, matchId, gameIndex + 1, {
        map_number: gameIndex + 1,
        team_a_id: matchId, // Will be resolved on backend
        team_b_id: matchId, // Will be resolved on backend
        score_a: gameResult.score_a,
        score_b: gameResult.score_b,
        kills_a: gameResult.kills_a,
        kills_b: gameResult.kills_b,
        deaths_a: gameResult.deaths_a,
        deaths_b: gameResult.deaths_b,
        winner_team_id: gameResult.winner_team_id || undefined,
        status: 'COMPLETED',
        scheduled_date: gameResult.scheduled_date || undefined,
        start_time: gameResult.start_time || undefined,
        end_time: gameResult.end_time || undefined,
      })
      setMessage(`Game ${gameIndex + 1} berhasil disimpan`)
    } catch (err) {
      setMatchError(err instanceof Error ? err.message : 'Gagal menyimpan game')
    } finally {
      setSaving(false)
    }
  }

  const handleSubmitMatchResult = async (matchId: string, matchFormat: string = 'BO1') => {
    if (!token) return
    const data = matchResults[matchId]
    if (!data) return
    const match = schedule.find((m: any) => m.id === matchId)
    const teamAId = match?.team_a_id
    const teamBId = match?.team_b_id
    
    // For bracket matches (BO3/BO5/BO7), require game breakdown
    if (matchFormat !== 'BO1') {
      const gamesData = gameResults[matchId] || []
      const requiredWins = matchFormat === 'BO3' ? 2 : matchFormat === 'BO5' ? 3 : matchFormat === 'BO7' ? 4 : 1
      
      if (!data.winner_team_id || !data.loser_team_id) {
        setMatchError('Winner dan Loser harus dipilih')
        return
      }
      if (data.winner_team_id === data.loser_team_id) {
        setMatchError('Winner dan Loser tidak boleh sama')
        return
      }
      
      // Count wins from game results
      const teamAWins = gamesData.filter((m) => m.winner_team_id === data.winner_team_id).length
      const teamBWins = gamesData.filter((m) => m.winner_team_id === data.loser_team_id).length
      
      if (data.winner_team_id && teamAWins !== requiredWins && teamBWins !== requiredWins) {
        setMatchError(`Breakdown harus menunjukkan ${requiredWins} kemenangan untuk winner`)
        return
      }
      
      setSaving(true)
      setMatchError(null)
      try {
        const payload = {
          ...data,
          map_results: gamesData.map((m, idx) => ({
            map_number: m.game_number || idx + 1,
            team_a_id: teamAId,
            team_b_id: teamBId,
            winner_team_id: m.winner_team_id,
            score_a: m.score_a,
            score_b: m.score_b,
            kills_a: m.kills_a,
            kills_b: m.kills_b,
            deaths_a: m.deaths_a,
            deaths_b: m.deaths_b,
            status: 'COMPLETED',
          })),
        }
        await adminSubmitMatchResult(token, tournamentId, matchId, payload)
        setMessage('Hasil pertandingan berhasil disimpan')
        setMatchResults((prev) => { const next = { ...prev }; delete next[matchId]; return next })
        setGameResults((prev) => { const next = { ...prev }; delete next[matchId]; return next })
        load()
      } catch (err) {
        setMatchError(err instanceof Error ? err.message : 'Gagal menyimpan hasil')
      } finally {
        setSaving(false)
      }
      return
    }
    
    // Group stage (BO1) logic
    if (data.score_a === data.score_b) {
      setMatchError('Score tidak boleh sama')
      return
    }
    if (!data.winner_team_id || !data.loser_team_id) {
      setMatchError('Winner dan Loser harus dipilih')
      return
    }
    if (data.winner_team_id === data.loser_team_id) {
      setMatchError('Winner dan Loser tidak boleh sama')
      return
    }
    setSaving(true)
    setMatchError(null)
    try {
      await adminSubmitMatchResult(token, tournamentId, matchId, data)
      setMessage('Hasil pertandingan berhasil disimpan')
      setMatchResults((prev) => { const next = { ...prev }; delete next[matchId]; return next })
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

  if (!tournamentData) {
    return <div className="flex items-center justify-center py-20"><div className="text-sm text-gray-400">Memuat turnamen...</div></div>
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
          <h2 className="text-2xl font-bold text-white">{tournamentData.name}</h2>
          <p className="mt-1 text-sm text-gray-400">Status: {tournamentData.status}</p>
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
                defaultValue={tournamentData.name}
                onBlur={(e) => handleUpdate({ name: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-300">Deskripsi</label>
              <textarea
                defaultValue={tournamentData.description || ''}
                onBlur={(e) => handleUpdate({ description: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
                rows={3}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-300">Timezone</label>
              <input
                type="text"
                defaultValue={tournamentData.timezone}
                onBlur={(e) => handleUpdate({ timezone: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-300">Third Place Mode</label>
              <select
                defaultValue={tournamentData.third_place_mode}
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
        <div className="space-y-8">
          {/* GROUP STAGE SECTION */}
          <div>
            <h3 className="mb-4 text-lg font-semibold text-blue-300">Group Stage</h3>
            <div className="flex flex-wrap items-center justify-between gap-2">
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

          {/* KLASEMEN SECTION */}
          <div>
            <h3 className="mb-4 text-lg font-semibold text-brand-300">Klasemen</h3>
            {standings.length === 0 ? (
              <Card><p className="text-sm text-gray-400">Belum ada data klasemen.</p></Card>
            ) : (
              <div className="space-y-4">
                {standings.map((group: any) => (
                  <Card key={group.group_id}>
                    <h4 className="mb-3 text-base font-semibold text-white">{group.group_name}</h4>
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
                            const qualification = bracketQualifications.find((q: any) => q.team_id === s.team_id && q.group_id === group.group_id)
                            const rank = s.rank || 999
                            const isUpper = rank >= 1 && rank <= 4
                            const isLower = rank >= 5 && rank <= 8
                            const isEliminated = rank > 8
                            const rowClass = isUpper ? 'bg-blue-500/5 border-blue-500/10' : isLower ? 'bg-green-500/5 border-green-500/10' : isEliminated ? 'bg-red-500/5 border-red-500/10' : 'border-white/5'
                            const nameClass = isUpper ? 'text-blue-300' : isLower ? 'text-green-300' : isEliminated ? 'text-red-300' : 'text-white'
                            return (
                              <tr key={s.team_id} className={`border-b ${rowClass}`}>
                                <td className="py-2 pr-4 text-gray-300">{s.rank || '-'}</td>
                                <td className={`py-2 pr-4 ${nameClass}`}>{s.team_name || s.team_id}</td>
                                <td className="py-2 pr-4 text-gray-300">{s.played}</td>
                                <td className="py-2 pr-4 text-green-400">{s.win}</td>
                                <td className="py-2 pr-4 text-red-400">{s.loss}</td>
                                <td className="py-2 pr-4 text-gray-300">{s.kill}</td>
                                <td className="py-2 pr-4 text-gray-300">{s.death}</td>
                                <td className="py-2 pr-4 text-gray-300">{s.kill_difference > 0 ? '+' : ''}{s.kill_difference}</td>
                                <td className="py-2 pr-4 text-gray-300">{winRate}%</td>
                                <td className="py-2 pr-4">
                                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                                    isUpper ? 'bg-blue-500/10 text-blue-300' :
                                    isLower ? 'bg-green-500/10 text-green-300' :
                                    isEliminated ? 'bg-red-500/10 text-red-300' : 'bg-gray-500/10 text-gray-300'
                                  }`}>
                                    {isUpper ? 'Upper' : isLower ? 'Lower' : isEliminated ? 'Eliminated' : '-'}
                                  </span>
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
          </div>
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
            <div className="space-y-6">
              {Object.entries(groupScheduleByStage(schedule)).map(([stage, stageMatches]) => {
                const stageLabel = stage === 'GROUP_STAGE' ? 'GROUP STAGE' : 'BRACKET'
                const stageColor = stage === 'GROUP_STAGE' ? 'text-blue-300' : 'text-brand-300'
                return (
                  <div key={stage}>
                    <h3 className={`mb-2 text-lg font-semibold ${stageColor}`}>{stageLabel}</h3>
                    <div className="space-y-2">
                      {stageMatches.map((m: any) => {
                        const result = matchResults[m.id] || { score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0 }
                        const isCompleted = m.status === 'COMPLETED'
                        const games = m.format === 'BO3' ? 3 : m.format === 'BO5' ? 5 : m.format === 'BO7' ? 7 : 1
                        return (
                          <Card key={m.id}>
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div>
                                <div className="text-sm font-medium text-white">{getTeamName(m.team_a_id)} vs {getTeamName(m.team_b_id)}</div>
                                <div className="text-xs text-gray-400">{m.scheduled_date || '—'} • {m.start_time || '—'} - {m.end_time || '—'} • {m.format}</div>
                              </div>
                              <span className={`rounded-full px-2 py-1 text-xs font-medium ${isCompleted ? 'bg-green-500/10 text-green-300' : 'bg-gray-500/10 text-gray-300'}`}>
                                {m.status}
                              </span>
                            </div>
                            {isCompleted && (
                              <div className="mt-2 text-sm font-semibold text-white">
                                {m.score_a} - {m.score_b}
                                {m.winner_team_id && <span className="ml-2 text-green-400">Win: {getTeamName(m.winner_team_id)}</span>}
                                <span className="ml-2 text-gray-400">K: {m.kills_a}-{m.kills_b} D: {m.deaths_a}-{m.deaths_b}</span>
                              </div>
                            )}
                            {!isCompleted && (
                              <div className="mt-3 space-y-2">
                                <div className="grid gap-2 md:grid-cols-2">
                                  <div>
                                    <label className="mb-1 block text-xs text-gray-400">Score {getTeamName(m.team_a_id)}</label>
                                    <input
                                      type="number"
                                      min={0}
                                      value={result.score_a}
                                      onChange={(e) => updateMatchResult(m.id, 'score_a', parseInt(e.target.value || '0', 10))}
                                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                    />
                                  </div>
                                  <div>
                                    <label className="mb-1 block text-xs text-gray-400">Score {getTeamName(m.team_b_id)}</label>
                                    <input
                                      type="number"
                                      min={0}
                                      value={result.score_b}
                                      onChange={(e) => updateMatchResult(m.id, 'score_b', parseInt(e.target.value || '0', 10))}
                                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                    />
                                  </div>
                                  <div>
                                    <label className="mb-1 block text-xs text-gray-400">Kills {getTeamName(m.team_a_id)}</label>
                                    <input
                                      type="number"
                                      min={0}
                                      value={result.kills_a}
                                      onChange={(e) => updateMatchResult(m.id, 'kills_a', parseInt(e.target.value || '0', 10))}
                                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                    />
                                  </div>
                                  <div>
                                    <label className="mb-1 block text-xs text-gray-400">Kills {getTeamName(m.team_b_id)}</label>
                                    <input
                                      type="number"
                                      min={0}
                                      value={result.kills_b}
                                      onChange={(e) => updateMatchResult(m.id, 'kills_b', parseInt(e.target.value || '0', 10))}
                                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                    />
                                  </div>
                                  <div>
                                    <label className="mb-1 block text-xs text-gray-400">Deaths {getTeamName(m.team_a_id)}</label>
                                    <input
                                      type="number"
                                      min={0}
                                      value={result.deaths_a}
                                      onChange={(e) => updateMatchResult(m.id, 'deaths_a', parseInt(e.target.value || '0', 10))}
                                      className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                    />
                                   </div>
                                   <div>
                                     <label className="mb-1 block text-xs text-gray-400">Deaths {getTeamName(m.team_b_id)}</label>
                                     <input
                                       type="number"
                                       min={0}
                                       value={result.deaths_b}
                                       onChange={(e) => updateMatchResult(m.id, 'deaths_b', parseInt(e.target.value || '0', 10))}
                                       className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                     />
                                    </div>
                                  </div>
                                  <div className="grid gap-2 md:grid-cols-2">
                                    <div>
                                      <label className="mb-1 block text-xs text-gray-400">Winner</label>
                                      <select
                                        value={result.winner_team_id || ''}
                                        onChange={(e) => updateMatchResult(m.id, 'winner_team_id', e.target.value)}
                                        className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                      >
                                        <option value="">- Pilih Winner -</option>
                                        <option value={m.team_a_id}>{getTeamName(m.team_a_id)}</option>
                                        <option value={m.team_b_id}>{getTeamName(m.team_b_id)}</option>
                                      </select>
                                    </div>
                                    <div>
                                      <label className="mb-1 block text-xs text-gray-400">Loser</label>
                                      <select
                                        value={result.loser_team_id || ''}
                                        onChange={(e) => updateMatchResult(m.id, 'loser_team_id', e.target.value)}
                                        className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                      >
                                        <option value="">- Pilih Loser -</option>
                                        <option value={m.team_a_id}>{getTeamName(m.team_a_id)}</option>
                                        <option value={m.team_b_id}>{getTeamName(m.team_b_id)}</option>
                                      </select>
                                    </div>
                                  </div>
                                  {m.format !== 'BO1' && (
                                    <div className="space-y-3">
                                      <label className="mb-1 block text-xs text-gray-400">Breakdown Pertandingan</label>
                                      {Array.from({ length: games }, (_, i) => {
                                        const gameResult = (gameResults[m.id] || [])[i] || { score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }
                                        return (
                                          <div key={i} className="rounded-lg border border-white/10 bg-surface-900/40 p-3">
                                            <div className="mb-2 text-xs font-medium text-gray-400">Game {i + 1}</div>
                                            <div className="grid gap-2 md:grid-cols-2">
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Score {getTeamName(m.team_a_id)}</label>
                                                <input
                                                  type="number"
                                                  min={0}
                                                  value={gameResult.score_a}
                                                  onChange={(e) => {
                                                    const value = parseInt(e.target.value || '0', 10)
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], score_a: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                />
                                              </div>
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Score {getTeamName(m.team_b_id)}</label>
                                                <input
                                                  type="number"
                                                  min={0}
                                                  value={gameResult.score_b}
                                                  onChange={(e) => {
                                                    const value = parseInt(e.target.value || '0', 10)
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], score_b: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                />
                                              </div>
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Kills {getTeamName(m.team_a_id)}</label>
                                                <input
                                                  type="number"
                                                  min={0}
                                                  value={gameResult.kills_a}
                                                  onChange={(e) => {
                                                    const value = parseInt(e.target.value || '0', 10)
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], kills_a: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                />
                                              </div>
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Kills {getTeamName(m.team_b_id)}</label>
                                                <input
                                                  type="number"
                                                  min={0}
                                                  value={gameResult.kills_b}
                                                  onChange={(e) => {
                                                    const value = parseInt(e.target.value || '0', 10)
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], kills_b: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                />
                                              </div>
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Deaths {getTeamName(m.team_a_id)}</label>
                                                <input
                                                  type="number"
                                                  min={0}
                                                  value={gameResult.deaths_a}
                                                  onChange={(e) => {
                                                    const value = parseInt(e.target.value || '0', 10)
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], deaths_a: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                />
                                             </div>
                                             <div>
                                               <label className="mb-1 block text-xs text-gray-400">Deaths {getTeamName(m.team_b_id)}</label>
                                               <input
                                                 type="number"
                                                 min={0}
                                                 value={gameResult.deaths_b}
                                                 onChange={(e) => {
                                                   const value = parseInt(e.target.value || '0', 10)
                                                   setGameResults((prev) => {
                                                     const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                     const updated = [...current]
                                                     updated[i] = { ...updated[i], deaths_b: value }
                                                     return { ...prev, [m.id]: updated }
                                                   })
                                                 }}
                                                 className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                               />
                                              </div>
                                            </div>
                                            <div className="grid gap-2 md:grid-cols-2">
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Winner Game {i + 1}</label>
                                                <select
                                                  value={gameResult.winner_team_id || ''}
                                                  onChange={(e) => {
                                                    const value = e.target.value
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], winner_team_id: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                >
                                                  <option value="">- Pilih Winner -</option>
                                                  <option value={m.team_a_id}>{getTeamName(m.team_a_id)}</option>
                                                  <option value={m.team_b_id}>{getTeamName(m.team_b_id)}</option>
                                                </select>
                                              </div>
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Tanggal</label>
                                                <input
                                                  type="date"
                                                  value={gameResult.scheduled_date || m.scheduled_date || ''}
                                                  onChange={(e) => {
                                                    const value = e.target.value
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], scheduled_date: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                />
                                              </div>
                                            </div>
                                            <div className="grid gap-2 md:grid-cols-2">
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Waktu Mulai</label>
                                                <input
                                                  type="time"
                                                  value={gameResult.start_time || ''}
                                                  onChange={(e) => {
                                                    const value = e.target.value
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], start_time: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                />
                                              </div>
                                              <div>
                                                <label className="mb-1 block text-xs text-gray-400">Waktu Selesai</label>
                                                <input
                                                  type="time"
                                                  value={gameResult.end_time || ''}
                                                  onChange={(e) => {
                                                    const value = e.target.value
                                                    setGameResults((prev) => {
                                                      const current = prev[m.id] || Array.from({ length: games }, (_, idx) => ({ game_number: idx + 1, score_a: 0, score_b: 0, kills_a: 0, kills_b: 0, deaths_a: 0, deaths_b: 0, winner_team_id: '' }))
                                                      const updated = [...current]
                                                      updated[i] = { ...updated[i], end_time: value }
                                                      return { ...prev, [m.id]: updated }
                                                    })
                                                  }}
                                                  className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
                                                />
                                              </div>
                                            </div>
                                            <button
                                              onClick={() => handleSubmitGameResult(m.id, i, m.format)}
                                              disabled={saving}
                                              className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-500 disabled:opacity-50"
                                            >
                                              Simpan Game {i + 1}
                                            </button>
                                          </div>
                                        )
                                      })}
                                    </div>
                                  )}
                                  <button
                                    onClick={() => handleSubmitMatchResult(m.id, m.format)}
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
                    </div>
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
                    <div className="text-sm font-medium text-white">{getTeamName(m.team_a_id)} vs {getTeamName(m.team_b_id)}</div>
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
                      const qualification = bracketQualifications.find((q: any) => q.team_id === s.team_id && q.group_id === group.group_id)
                      const rank = s.rank || 999
                      const isUpper = rank >= 1 && rank <= 4
                      const isLower = rank >= 5 && rank <= 8
                      const isEliminated = rank > 8
                      const rowClass = isUpper ? 'bg-blue-500/5 border-blue-500/10' : isLower ? 'bg-green-500/5 border-green-500/10' : isEliminated ? 'bg-red-500/5 border-red-500/10' : 'border-white/5'
                      const nameClass = isUpper ? 'text-blue-300' : isLower ? 'text-green-300' : isEliminated ? 'text-red-300' : 'text-white'
                      return (
                        <tr key={s.team_id} className={`border-b ${rowClass}`}>
                          <td className="py-2 pr-4 text-gray-300">{s.rank || '-'}</td>
                          <td className={`py-2 pr-4 ${nameClass}`}>{s.team_name || s.team_id}</td>
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
          {/* Daily Standings */}
          <Card>
            <h3 className="mb-3 text-lg font-semibold text-white">Klasemen Harian</h3>
            <div className="mb-3 flex items-center gap-2">
              <label className="text-xs text-gray-400">Tanggal:</label>
              <select
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="">- Pilih Tanggal -</option>
                {Array.from(new Set(schedule.map((m: any) => m.scheduled_date).filter(Boolean))).sort().map((date: string) => (
                  <option key={date} value={date}>{date}</option>
                ))}
              </select>
            </div>
            {dailyStandings.length === 0 ? (
              <p className="text-sm text-gray-400">Belum ada data klasemen harian untuk tanggal ini.</p>
            ) : (
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
                    {dailyStandings.map((s: any, idx: number) => (
                      <tr key={s.team_id} className="border-b border-white/5">
                        <td className="py-2 pr-4 text-gray-300">{idx + 1}</td>
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
            )}
          </Card>
        </div>
      )}

      {activeTab === 'knockout' && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={async () => {
                if (!token) return
                try {
                  await adminGenerateKnockout(token, tournamentId, [], true)
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
                  await adminResolveKnockout(token, tournamentId)
                  setBracketResolved(true)
                  load()
                } catch (err) {
                  alert(err instanceof Error ? err.message : 'Gagal resolve bracket')
                }
              }}
              disabled={!knockout || (knockout.upper_matches?.length === 0 && knockout.lower_matches?.length === 0 && !knockout.grand_final)}
              className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              Resolve Bracket
            </button>
            <button
              onClick={async () => {
                if (!token) return
                try {
                  await adminResetBracket(token, tournamentId)
                  load()
                } catch (err) {
                  alert(err instanceof Error ? err.message : 'Gagal reset bracket')
                }
              }}
              disabled={!knockout || (knockout.upper_matches?.length === 0 && knockout.lower_matches?.length === 0 && !knockout.grand_final)}
              className="rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              Reset Bracket
            </button>
          </div>
          {!knockout || (knockout.upper_matches?.length === 0 && knockout.lower_matches?.length === 0 && !knockout.grand_final) ? (
            <Card><p className="text-sm text-gray-400">Belum ada bracket.</p></Card>
          ) : (
            <AnimatedBracket
              upperMatches={knockout.upper_matches || []}
              lowerMatches={knockout.lower_matches || []}
              grandFinal={knockout.grand_final || null}
              token={token}
              tournamentId={tournamentId}
              getTeamName={getTeamName}
              onMatchUpdate={load}
              onAdvance={async (matchId: string) => {
                if (!token) return
                await adminAdvanceKnockout(token, tournamentId, matchId)
                load()
              }}
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
                    <div className="text-sm font-medium text-white">{getTeamName(m.team_a_id)} vs {getTeamName(m.team_b_id)}</div>
                    <div className="text-xs text-gray-400">{m.stage} • {m.scheduled_date}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${m.winner_team_id ? 'bg-green-500/10 text-green-300' : 'bg-gray-500/10 text-gray-300'}`}>
                      {m.score_a} - {m.score_b}
                    </span>
                    {m.winner_team_id && (
                      <span className="text-xs text-green-400">
                        Win: {m.winner_team_id}
                      </span>
                    )}
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
