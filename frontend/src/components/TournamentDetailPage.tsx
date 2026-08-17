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
  const [knockout, setKnockout] = useState<BracketResponse | null>(null)
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
        setKnockout(k as BracketResponse)
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
          {!knockout || (!knockout.upper_matches?.length && !knockout.lower_matches?.length && !knockout.grand_final) ? (
            <Card><p className="text-sm text-gray-400">Belum ada bracket.</p></Card>
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Upper Bracket */}
              <Card>
                <h3 className="mb-4 text-lg font-semibold text-green-300">Upper Bracket</h3>
                <div className="space-y-3">
                  {knockout.upper_matches?.map((match) => (
                    <div key={match.id} className="rounded-xl border border-white/10 bg-surface-900/60 p-3">
                      <div className="mb-1 text-xs text-gray-400">
                        Match {match.match_number} ({match.format})
                        {match.is_upper_final && ' - Upper Final'}
                      </div>
                      <div className="space-y-1">
                        <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${match.winner_team_id === match.team_a_id ? 'bg-white/10' : 'bg-white/5'}`}>
                          <span className="text-sm font-medium">{match.team_a_id || 'TBD'}</span>
                          {match.score_a !== undefined && <span className="text-xs">{match.score_a}</span>}
                        </div>
                        <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${match.winner_team_id === match.team_b_id ? 'bg-white/10' : 'bg-white/5'}`}>
                          <span className="text-sm font-medium">{match.team_b_id || 'TBD'}</span>
                          {match.score_b !== undefined && <span className="text-xs">{match.score_b}</span>}
                        </div>
                      </div>
                      {match.status === 'COMPLETED' && match.winner_team_id && (
                        <div className="mt-2 text-xs text-green-400">
                          Winner: {match.winner_team_id}
                        </div>
                      )}
                    </div>
                  ))}
                  {(!knockout.upper_matches || knockout.upper_matches.length === 0) && (
                    <p className="text-xs text-gray-500">Belum ada match upper bracket.</p>
                  )}
                </div>
              </Card>

              {/* Lower Bracket */}
              <Card>
                <h3 className="mb-4 text-lg font-semibold text-yellow-300">Lower Bracket</h3>
                <div className="space-y-3">
                  {knockout.lower_matches?.map((match) => (
                    <div key={match.id} className="rounded-xl border border-white/10 bg-surface-900/60 p-3">
                      <div className="mb-1 text-xs text-gray-400">
                        Match {match.match_number} ({match.format})
                        {match.is_lower_final && ' - Lower Final'}
                      </div>
                      <div className="space-y-1">
                        <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${match.winner_team_id === match.team_a_id ? 'bg-white/10' : 'bg-white/5'}`}>
                          <span className="text-sm font-medium">{match.team_a_id || 'TBD'}</span>
                          {match.score_a !== undefined && <span className="text-xs">{match.score_a}</span>}
                        </div>
                        <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${match.winner_team_id === match.team_b_id ? 'bg-white/10' : 'bg-white/5'}`}>
                          <span className="text-sm font-medium">{match.team_b_id || 'TBD'}</span>
                          {match.score_b !== undefined && <span className="text-xs">{match.score_b}</span>}
                        </div>
                      </div>
                      {match.status === 'COMPLETED' && match.winner_team_id && (
                        <div className="mt-2 text-xs text-green-400">
                          Winner: {match.winner_team_id}
                        </div>
                      )}
                    </div>
                  ))}
                  {(!knockout.lower_matches || knockout.lower_matches.length === 0) && (
                    <p className="text-xs text-gray-500">Belum ada match lower bracket.</p>
                  )}
                </div>
              </Card>
            </div>
          )}

          {/* Grand Final and Lower Final */}
          {(knockout && (knockout.grand_final || knockout.lower_final)) && (
            <div className="grid gap-6 lg:grid-cols-2">
              {knockout.lower_final && (
                <Card>
                  <h3 className="mb-4 text-lg font-semibold text-brand-300">Lower Final (BO5)</h3>
                  <div className="rounded-xl border border-white/10 bg-surface-900/60 p-3">
                    <div className="mb-1 text-xs text-gray-400">Match 9</div>
                    <div className="space-y-1">
                      <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${knockout.lower_final.winner_team_id === knockout.lower_final.team_a_id ? 'bg-white/10' : 'bg-white/5'}`}>
                        <span className="text-sm font-medium">{knockout.lower_final.team_a_id || 'TBD'}</span>
                        {knockout.lower_final.score_a !== undefined && <span className="text-xs">{knockout.lower_final.score_a}</span>}
                      </div>
                      <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${knockout.lower_final.winner_team_id === knockout.lower_final.team_b_id ? 'bg-white/10' : 'bg-white/5'}`}>
                        <span className="text-sm font-medium">{knockout.lower_final.team_b_id || 'TBD'}</span>
                        {knockout.lower_final.score_b !== undefined && <span className="text-xs">{knockout.lower_final.score_b}</span>}
                      </div>
                    </div>
                    {knockout.lower_final.status === 'COMPLETED' && knockout.lower_final.winner_team_id && (
                      <div className="mt-2 text-xs text-green-400">
                        Winner: {knockout.lower_final.winner_team_id}
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {knockout.grand_final && (
                <Card>
                  <h3 className="mb-4 text-lg font-semibold text-purple-300">Grand Final (BO7)</h3>
                  <div className="rounded-xl border border-purple-500/30 bg-purple-500/5 p-3">
                    <div className="mb-1 text-xs text-gray-400">Match 10</div>
                    <div className="space-y-1">
                      <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${knockout.grand_final.winner_team_id === knockout.grand_final.team_a_id ? 'bg-white/10' : 'bg-white/5'}`}>
                        <span className="text-sm font-medium">{knockout.grand_final.team_a_id || 'TBD'}</span>
                        {knockout.grand_final.score_a !== undefined && <span className="text-xs">{knockout.grand_final.score_a}</span>}
                      </div>
                      <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${knockout.grand_final.winner_team_id === knockout.grand_final.team_b_id ? 'bg-white/10' : 'bg-white/5'}`}>
                        <span className="text-sm font-medium">{knockout.grand_final.team_b_id || 'TBD'}</span>
                        {knockout.grand_final.score_b !== undefined && <span className="text-xs">{knockout.grand_final.score_b}</span>}
                      </div>
                    </div>
                    {knockout.grand_final.status === 'COMPLETED' && knockout.grand_final.winner_team_id && (
                      <div className="mt-2 text-xs text-green-400">
                        Winner: {knockout.grand_final.winner_team_id}
                      </div>
                    )}
                  </div>
                </Card>
              )}
            </div>
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
