'use client'

import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

interface BracketMatch {
  id: string
  team_a_id: string | null
  team_b_id: string | null
  winner_team_id: string | null
  status: string
  format: string
  score_a?: number
  score_b?: number
  round: number
  bracket_type: 'UPPER' | 'LOWER'
  is_upper_final?: boolean
  is_lower_final?: boolean
  is_grand_final?: boolean
  map_results?: Array<{
    id?: string
    map_number: number
    winner_team_id?: string
    score_a?: number
    score_b?: number
    kills_a?: number
    kills_b?: number
    deaths_a?: number
    deaths_b?: number
    status?: string
  }>
}

interface BracketProps {
  upperMatches: BracketMatch[]
  lowerMatches: BracketMatch[]
  grandFinal: BracketMatch | null
  token: string | null
  tournamentId: string
  onMatchUpdate?: () => void
}

function getRequiredWins(format: string): number {
  switch (format) {
    case 'BO3':
      return 2
    case 'BO5':
      return 3
    case 'BO7':
      return 4
    default:
      return 1
  }
}

function BracketMatchCard({ match, index, isFinal, isGrandFinal, token, tournamentId, onMatchUpdate }: { match: BracketMatch; index: number; isFinal?: boolean; isGrandFinal?: boolean; token: string | null; tournamentId: string; onMatchUpdate?: () => void }) {
  const [animated, setAnimated] = useState(false)
  const [mapResults, setMapResults] = useState<Record<number, { team_a_wins: number; team_b_wins: number; maps: any[] }>>({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), index * 100)
    return () => clearTimeout(timer)
  }, [index])

  useEffect(() => {
    if (match.map_results && match.map_results.length > 0) {
      const grouped: Record<number, any> = {}
      match.map_results.forEach(m => {
        if (m.map_number !== undefined) {
          grouped[m.map_number] = m
        }
      })
      setMapResults(grouped)
    }
  }, [match.map_results])

  const getBorderColor = () => {
    if (isGrandFinal) return 'border-purple-500/50 bg-purple-500/5'
    if (isFinal) return 'border-brand-500/50 bg-brand-500/5'
    if (match.bracket_type === 'UPPER') return 'border-green-500/30 bg-green-500/5'
    return 'border-yellow-500/30 bg-yellow-500/5'
  }

  const getTextColor = () => {
    if (isGrandFinal) return 'text-purple-300'
    if (isFinal) return 'text-brand-300'
    if (match.bracket_type === 'UPPER') return 'text-green-300'
    return 'text-yellow-300'
  }

  const requiredWins = getRequiredWins(match.format)

  const handleMapSubmit = async (mapNumber: number, teamAWin: boolean) => {
    if (!token || submitting) return
    setSubmitting(true)
    try {
      const currentResults = mapResults[mapNumber]?.maps || []
      const newMapResult = {
        map_number: mapNumber,
        team_a_id: match.team_a_id,
        team_b_id: match.team_b_id,
        winner_team_id: teamAWin ? match.team_a_id : match.team_b_id,
        score_a: teamAWin ? 1 : 0,
        score_b: teamAWin ? 0 : 1,
        status: 'COMPLETED',
      }
      const updatedResults = [...currentResults, newMapResult]
      const teamAWinCount = updatedResults.filter(r => r.winner_team_id === match.team_a_id).length
      const teamBWinCount = updatedResults.filter(r => r.winner_team_id === match.team_b_id).length
      const overallScoreA = teamAWinCount
      const overallScoreB = teamBWinCount
      const isComplete = teamAWinCount >= requiredWins || teamBWinCount >= requiredWins
      await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/matches/${encodeURIComponent(match.id)}/result`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Token': token,
        },
        body: JSON.stringify({
          score_a: overallScoreA,
          score_b: overallScoreB,
          map_results: updatedResults,
        }),
      })
      if (onMatchUpdate) onMatchUpdate()
    } catch (err) {
      console.error('Failed to submit map result:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const renderMapInput = (mapNumber: number) => {
    const existing = mapResults[mapNumber]
    const lastMap = existing?.maps?.[existing.maps.length - 1]
    return (
      <div key={mapNumber} className="flex items-center justify-between rounded-lg border border-white/10 bg-surface-900/40 px-3 py-2">
        <span className="text-xs text-gray-400">Map {mapNumber}</span>
        {lastMap ? (
          <div className="flex items-center gap-2">
            <span className={`text-xs ${lastMap.winner_team_id === match.team_a_id ? 'text-green-400' : 'text-red-400'}`}>
              {lastMap.winner_team_id === match.team_a_id ? match.team_a_id : match.team_b_id} wins
            </span>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => handleMapSubmit(mapNumber, true)}
              disabled={submitting}
              className="rounded-lg border border-green-500/30 px-2 py-1 text-xs text-green-300 hover:bg-green-500/10 disabled:opacity-50"
            >
              {match.team_a_id} Win
            </button>
            <button
              onClick={() => handleMapSubmit(mapNumber, false)}
              disabled={submitting}
              className="rounded-lg border border-red-500/30 px-2 py-1 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-50"
            >
              {match.team_b_id} Win
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className={`rounded-xl border p-3 transition-all duration-500 ${getBorderColor()} ${animated ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'}`}
    >
      <div className="mb-1 text-xs text-gray-400">
        {isGrandFinal ? 'Final' : isFinal ? 'Final' : `Round ${match.round}`}
        <span className="ml-2 text-gray-500">({match.format})</span>
      </div>
      <div className={`space-y-1 ${getTextColor()}`}>
        <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${match.winner_team_id === match.team_a_id ? 'bg-white/10' : 'bg-white/5'}`}>
          <span className="text-sm font-medium">{match.team_a_id || 'TBD'}</span>
          {match.score_a !== undefined && <span className="text-xs">{match.score_a}</span>}
        </div>
        <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${match.winner_team_id === match.team_b_id ? 'bg-white/10' : 'bg-white/5'}`}>
          <span className="text-sm font-medium">{match.team_b_id || 'TBD'}</span>
          {match.score_b !== undefined && <span className="text-xs">{match.score_b}</span>}
        </div>
      </div>
      {match.status !== 'COMPLETED' && match.team_a_id && match.team_b_id && (
        <div className="mt-2 space-y-1">
          {Array.from({ length: Math.min(requiredWins * 2 - 1, 7) }, (_, i) => renderMapInput(i + 1))}
        </div>
      )}
      {match.status === 'COMPLETED' && match.winner_team_id && (
        <div className="mt-2 text-xs text-green-400">
          Winner: {match.winner_team_id}
        </div>
      )}
    </div>
  )
}

export default function AnimatedBracket({ upperMatches, lowerMatches, grandFinal, token, tournamentId, onMatchUpdate }: BracketProps) {
  const [showUpper, setShowUpper] = useState(false)
  const [showLower, setShowLower] = useState(false)
  const [showGrandFinal, setShowGrandFinal] = useState(false)

  useEffect(() => {
    const upperTimer = setTimeout(() => setShowUpper(true), 200)
    const lowerTimer = setTimeout(() => setShowLower(true), 600)
    const grandFinalTimer = setTimeout(() => setShowGrandFinal(true), 1000)
    return () => {
      clearTimeout(upperTimer)
      clearTimeout(lowerTimer)
      clearTimeout(grandFinalTimer)
    }
  }, [])

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upper Bracket */}
        <div className={`space-y-3 transition-all duration-700 ${showUpper ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-green-500"></div>
            <h3 className="text-lg font-semibold text-green-300">Upper Bracket</h3>
          </div>
          <div className="space-y-2">
            {upperMatches.map((match, idx) => (
              <BracketMatchCard
                key={match.id}
                match={match}
                index={idx}
                isFinal={match.is_upper_final}
                token={token}
                tournamentId={tournamentId}
                onMatchUpdate={onMatchUpdate}
              />
            ))}
            {upperMatches.length === 0 && (
              <p className="text-xs text-gray-500">Belum ada match upper bracket.</p>
            )}
          </div>
        </div>

        {/* Lower Bracket */}
        <div className={`space-y-3 transition-all duration-700 ${showLower ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-yellow-500"></div>
            <h3 className="text-lg font-semibold text-yellow-300">Lower Bracket</h3>
          </div>
          <div className="space-y-2">
            {lowerMatches.map((match, idx) => (
              <BracketMatchCard
                key={match.id}
                match={match}
                index={idx}
                isFinal={match.is_lower_final}
                token={token}
                tournamentId={tournamentId}
                onMatchUpdate={onMatchUpdate}
              />
            ))}
            {lowerMatches.length === 0 && (
              <p className="text-xs text-gray-500">Belum ada match lower bracket.</p>
            )}
          </div>
        </div>
      </div>

      {/* Grand Final */}
      {grandFinal && (
        <div className={`flex justify-center transition-all duration-700 ${showGrandFinal ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}>
          <div className="w-full max-w-md">
            <div className="flex items-center justify-center gap-2 mb-3">
              <div className="h-4 w-4 rounded-full bg-purple-500"></div>
              <h3 className="text-xl font-bold text-purple-300">Grand Final (BO7)</h3>
            </div>
            <BracketMatchCard
              match={grandFinal}
              index={0}
              isGrandFinal
              token={token}
              tournamentId={tournamentId}
              onMatchUpdate={onMatchUpdate}
            />
          </div>
        </div>
      )}
    </div>
  )
}
