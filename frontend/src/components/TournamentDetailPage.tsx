'use client'

import { useState, useEffect } from 'react'
import { userGetTournament, userGetSchedule, userGetMatches, userGetStandings, userGetKnockout, userGetResults, userGetPlacements } from '@/lib/tournamentApi'
import { useAuthToken } from '@/lib/hooks/useAuth'
import { TournamentResponse, MatchResponse, StandingResponse, BracketResponse, PlacementResponse } from '@/types'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import { Trophy, Calendar, Table2, GitBranch, ClipboardList, Award } from 'lucide-react'

type Tab = 'overview' | 'schedule' | 'standings' | 'bracket' | 'results'

export default function TournamentDetailPage({ tournamentId, onBack }: { tournamentId: string; onBack: () => void }) {
  const token = useAuthToken()
  const [tournament, setTournament] = useState<TournamentResponse | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [schedule, setSchedule] = useState<MatchResponse[]>([])
  const [matches, setMatches] = useState<MatchResponse[]>([])
  const [standings, setStandings] = useState<any[]>([])
  const [knockout, setKnockout] = useState<BracketResponse[]>([])
  const [results, setResults] = useState<MatchResponse[]>([])
  const [placements, setPlacements] = useState<PlacementResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    setError(null)
    Promise.all([
      userGetTournament(token, tournamentId),
      userGetSchedule(token, tournamentId),
      userGetMatches(token, tournamentId),
      userGetStandings(token, tournamentId),
      userGetKnockout(token, tournamentId),
      userGetResults(token, tournamentId),
      userGetPlacements(token, tournamentId),
    ])
      .then(([t, s, m, st, k, r, p]) => {
        setTournament(t as TournamentResponse)
        setSchedule(s as MatchResponse[])
        setMatches(m as MatchResponse[])
        setStandings(st as any[])
        setKnockout(k as BracketResponse[])
        setResults(r as MatchResponse[])
        setPlacements(p as PlacementResponse[])
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [token, tournamentId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner text="Memuat detail turnamen..." />
      </div>
    )
  }

  if (error || !tournament) {
    return <ErrorMessage title="Error" message={error || 'Turnamen tidak ditemukan'} />
  }

  const tabs: { key: Tab; label: string; icon: any }[] = [
    { key: 'overview', label: 'Overview', icon: Trophy },
    { key: 'schedule', label: 'Jadwal', icon: Calendar },
    { key: 'standings', label: 'Klasemen', icon: Table2 },
    { key: 'bracket', label: 'Bracket', icon: GitBranch },
    { key: 'results', label: 'Hasil', icon: ClipboardList },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="text-sm text-gray-400 hover:text-white">
          ← Kembali
        </button>
        <div>
          <h2 className="text-2xl font-bold text-white">{tournament.name}</h2>
          <p className="mt-1 text-sm text-gray-400">{tournament.description}</p>
        </div>
      </div>

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

      {activeTab === 'overview' && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <div className="text-sm text-gray-400">Status</div>
            <div className="mt-1 text-2xl font-bold text-white">{tournament.status}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-400">Timezone</div>
            <div className="mt-1 text-2xl font-bold text-white">{tournament.timezone}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-400">Juara 1</div>
            <div className="mt-1 flex items-center gap-2 text-2xl font-bold text-yellow-400">
              <Trophy className="h-6 w-6" />
              {tournament.champion_team_id || '-'}
            </div>
          </Card>
          <Card>
            <div className="text-sm text-gray-400">Juara 2</div>
            <div className="mt-1 text-2xl font-bold text-gray-300">{tournament.runner_up_team_id || '-'}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-400">Juara 3</div>
            <div className="mt-1 text-2xl font-bold text-orange-400">{tournament.third_place_team_id || '-'}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-400">Total Match</div>
            <div className="mt-1 text-2xl font-bold text-white">{schedule.length}</div>
          </Card>
        </div>
      )}

      {activeTab === 'schedule' && (
        <div className="space-y-4">
          {schedule.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada jadwal.</p></Card>
          ) : (
            schedule.map((m) => (
              <Card key={m.id}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium text-white">
                      {m.team_a_id || 'TBD'} vs {m.team_b_id || 'TBD'}
                    </div>
                    <div className="text-xs text-gray-400">
                      {m.scheduled_date} • {m.start_time} - {m.end_time}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-brand-500/10 px-2 py-1 text-xs font-medium text-brand-300">
                      {m.format}
                    </span>
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                      m.status === 'COMPLETED' ? 'bg-green-500/10 text-green-300' :
                      m.status === 'ONGOING' ? 'bg-yellow-500/10 text-yellow-300' :
                      'bg-gray-500/10 text-gray-300'
                    }`}>
                      {m.status}
                    </span>
                  </div>
                </div>
                {m.status === 'COMPLETED' && (
                  <div className="mt-2 text-sm font-semibold text-white">
                    {m.score_a} - {m.score_b}
                    {m.winner_team_id && <span className="ml-2 text-green-400">Win</span>}
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'standings' && (
        <div className="space-y-4">
          {standings.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada klasemen.</p></Card>
          ) : (
            standings.map((group) => (
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
                      {group.standings.map((s: StandingResponse) => (
                        <tr key={s.team_id} className="border-b border-white/5">
                          <td className="py-2 pr-4 text-gray-300">{s.rank || '-'}</td>
                          <td className="py-2 pr-4 text-white">{s.team_id}</td>
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
            ))
          )}
        </div>
      )}

      {activeTab === 'bracket' && (
        <div className="space-y-6">
          {knockout.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada bracket.</p></Card>
          ) : (
            knockout.map((bracket) => (
              <Card key={bracket.id}>
                <h3 className="mb-4 text-lg font-semibold text-white">{bracket.name}</h3>
                <div className="space-y-4">
                  {bracket.rounds?.map((round) => (
                    <div key={round.id}>
                      <div className="mb-2 text-sm font-medium text-gray-400">{round.round_name}</div>
                      <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
                        {round.slots.map((slot) => (
                          <div
                            key={slot.id}
                            className={`rounded-xl border p-3 ${
                              slot.team_id ? 'border-white/10 bg-surface-900/60' : 'border-dashed border-white/5 bg-surface-900/20'
                            }`}
                          >
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
          {results.length === 0 ? (
            <Card><p className="text-sm text-gray-400">Belum ada hasil match.</p></Card>
          ) : (
            results.map((m) => (
              <Card key={m.id}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium text-white">
                      {m.team_a_id} vs {m.team_b_id}
                    </div>
                    <div className="text-xs text-gray-400">{m.stage} • {m.scheduled_date}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                      m.winner_team_id === m.team_a_id ? 'bg-green-500/10 text-green-300' : 'bg-gray-500/10 text-gray-300'
                    }`}>
                      {m.score_a} - {m.score_b}
                    </span>
                  </div>
                </div>
                {m.kills_a !== null && (
                  <div className="mt-2 text-xs text-gray-400">
                    Kills: {m.kills_a} - {m.kills_b} | Deaths: {m.deaths_a} - {m.deaths_b}
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  )
}
