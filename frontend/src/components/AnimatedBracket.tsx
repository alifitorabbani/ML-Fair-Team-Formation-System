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
  next_match_id?: string
  loser_next_match_id?: string
  match_number?: number
  participant_source_a?: string | null
  participant_source_b?: string | null
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
  getTeamName?: (teamId: string | null) => string
  onMatchUpdate?: () => void
  onAdvance?: (matchId: string) => void
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

const CARD_W = 220
const CARD_H = 80
const H_GAP = 40
const V_GAP = 28
const LOWER_COL_X = CARD_W + H_GAP

function getY(index: number, total: number, containerHeight: number): number {
  if (total === 1) return (containerHeight - CARD_H) / 2
  const spacing = (containerHeight - CARD_H) / (total - 1)
  return spacing * index
}

function getGrandFinalX(containerWidth: number): number {
  return (containerWidth - CARD_W) / 2
}

function BracketMatchCard({ match, index, isFinal, isGrandFinal, token, tournamentId, getTeamName, onMatchUpdate, onAdvance }: { match: BracketMatch; index: number; isFinal?: boolean; isGrandFinal?: boolean; token: string | null; tournamentId: string; getTeamName?: (teamId: string | null) => string; onMatchUpdate?: () => void; onAdvance?: (matchId: string) => void }) {
  const [animated, setAnimated] = useState(false)
  const [mapResults, setMapResults] = useState<Record<number, { team_a_wins: number; team_b_wins: number; maps: any[] }>>({})
  const [submitting, setSubmitting] = useState(false)
  const [advancing, setAdvancing] = useState(false)
  const [selectedWinner, setSelectedWinner] = useState<string>('')
  const [selectedLoser, setSelectedLoser] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

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

  const getLabel = () => {
    if (isGrandFinal) return 'Grand Final'
    if (isFinal) return match.bracket_type === 'UPPER' ? 'Upper Final' : 'Lower Final'
    if (match.bracket_type === 'UPPER') {
      return match.round === 1 ? 'Upper Round 1' : 'Upper Round 2'
    }
    if (match.round === 1) return 'Lower Round 1'
    if (match.round === 2) return 'Lower Round 2'
    return 'Lower Round 3'
  }

  const requiredWins = getRequiredWins(match.format)

  const displayTeamName = (teamId: string | null | undefined) => {
    if (!teamId) return 'TBD'
    if (getTeamName) return getTeamName(teamId)
    return teamId
  }

  const handleAdvance = async () => {
    if (!token || !onAdvance || advancing) return
    setAdvancing(true)
    try {
      await onAdvance(match.id)
    } catch (err) {
      console.error('Failed to advance match:', err)
    } finally {
      setAdvancing(false)
    }
  }

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

  const handleSubmitBracketResult = async () => {
    if (!token || submitting) return
    if (!selectedWinner || !selectedLoser) {
      setError('Pilih Winner dan Loser')
      return
    }
    if (selectedWinner === selectedLoser) {
      setError('Winner dan Loser tidak boleh sama')
      return
    }
    if (selectedWinner !== match.team_a_id && selectedWinner !== match.team_b_id) {
      setError('Winner harus salah satu peserta match')
      return
    }
    if (selectedLoser !== match.team_a_id && selectedLoser !== match.team_b_id) {
      setError('Loser harus salah satu peserta match')
      return
    }
    const allMaps = Object.values(mapResults).flatMap(m => m.maps)
    const teamAWinCount = allMaps.filter(r => r.winner_team_id === match.team_a_id).length
    const teamBWinCount = allMaps.filter(r => r.winner_team_id === match.team_b_id).length
    const requiredWinsForFormat = getRequiredWins(match.format)
    if (selectedWinner === match.team_a_id && teamAWinCount !== requiredWinsForFormat) {
      setError(`Breakdown menunjukkan ${teamAWinCount} kemenangan untuk tim A, tapi memerlukan ${requiredWinsForFormat} kemenangan untuk menjadi winner`)
      return
    }
    if (selectedWinner === match.team_b_id && teamBWinCount !== requiredWinsForFormat) {
      setError(`Breakdown menunjukkan ${teamBWinCount} kemenangan untuk tim B, tapi memerlukan ${requiredWinsForFormat} kemenangan untuk menjadi winner`)
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const scoreA = selectedWinner === match.team_a_id ? requiredWinsForFormat : teamAWinCount
      const scoreB = selectedWinner === match.team_b_id ? requiredWinsForFormat : teamBWinCount
      const mapResultsPayload = allMaps.map((m, idx) => ({
        map_number: idx + 1,
        team_a_id: match.team_a_id,
        team_b_id: match.team_b_id,
        winner_team_id: m.winner_team_id,
        score_a: m.score_a ?? 0,
        score_b: m.score_b ?? 0,
        status: 'COMPLETED',
      }))
      await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/matches/${encodeURIComponent(match.id)}/result`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Token': token,
        },
        body: JSON.stringify({
          score_a: scoreA,
          score_b: scoreB,
          winner_team_id: selectedWinner,
          loser_team_id: selectedLoser,
          map_results: mapResultsPayload,
        }),
      })
      if (onMatchUpdate) onMatchUpdate()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal menyimpan hasil')
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
              {displayTeamName(lastMap.winner_team_id)} wins
            </span>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => handleMapSubmit(mapNumber, true)}
              disabled={submitting}
              className="rounded-lg border border-green-500/30 px-2 py-1 text-xs text-green-300 hover:bg-green-500/10 disabled:opacity-50"
            >
              {displayTeamName(match.team_a_id)} Win
            </button>
            <button
              onClick={() => handleMapSubmit(mapNumber, false)}
              disabled={submitting}
              className="rounded-lg border border-red-500/30 px-2 py-1 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-50"
            >
              {displayTeamName(match.team_b_id)} Win
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className={`rounded-xl border p-3 transition-all duration-500 ${getBorderColor()} ${animated ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}`}
    >
      <div className="mb-1 flex items-center justify-between text-xs text-gray-400">
        <span>{getLabel()}</span>
        <span>{match.format}</span>
      </div>
      <div className={`space-y-1 ${getTextColor()}`}>
        <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${match.winner_team_id === match.team_a_id ? 'bg-white/10' : 'bg-white/5'}`}>
          <span className="text-sm font-medium">{displayTeamName(match.team_a_id)}</span>
          {match.score_a !== undefined && <span className="text-xs">{match.score_a}</span>}
        </div>
        <div className={`flex items-center justify-between rounded-lg px-2 py-1 ${match.winner_team_id === match.team_b_id ? 'bg-white/10' : 'bg-white/5'}`}>
          <span className="text-sm font-medium">{displayTeamName(match.team_b_id)}</span>
          {match.score_b !== undefined && <span className="text-xs">{match.score_b}</span>}
        </div>
      </div>
      {match.status !== 'COMPLETED' && match.team_a_id && match.team_b_id && (
        <div className="mt-2 space-y-1">
          {Array.from({ length: Math.min(requiredWins * 2 - 1, 7) }, (_, i) => renderMapInput(i + 1))}
        </div>
      )}
      {match.status === 'COMPLETED' && match.winner_team_id && (
        <div className="mt-2 space-y-2">
          <div className="text-xs text-green-400">
            Winner: {displayTeamName(match.winner_team_id)}
          </div>
          {onAdvance && match.next_match_id && (
            <button
              onClick={handleAdvance}
              disabled={advancing}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
            >
              {advancing ? 'Advancing...' : 'Advance Winner'}
            </button>
          )}
        </div>
      )}
      {match.status !== 'COMPLETED' && match.team_a_id && match.team_b_id && (
        <div className="mt-3 space-y-2">
          <div className="grid gap-2 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Winner</label>
              <select
                value={selectedWinner}
                onChange={(e) => { setSelectedWinner(e.target.value); setError(null) }}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="">- Pilih Winner -</option>
                <option value={match.team_a_id}>{displayTeamName(match.team_a_id)}</option>
                <option value={match.team_b_id}>{displayTeamName(match.team_b_id)}</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Loser</label>
              <select
                value={selectedLoser}
                onChange={(e) => { setSelectedLoser(e.target.value); setError(null) }}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-sm text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="">- Pilih Loser -</option>
                <option value={match.team_a_id}>{displayTeamName(match.team_a_id)}</option>
                <option value={match.team_b_id}>{displayTeamName(match.team_b_id)}</option>
              </select>
            </div>
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            onClick={handleSubmitBracketResult}
            disabled={submitting}
            className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
          >
            {submitting ? 'Menyimpan...' : 'Simpan Hasil Bracket'}
          </button>
        </div>
      )}
    </div>
  )
}

export default function AnimatedBracket({ upperMatches, lowerMatches, grandFinal, token, tournamentId, getTeamName, onMatchUpdate, onAdvance }: BracketProps) {
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

  // Organize matches by round
  const ubRound1 = upperMatches.filter(m => m.round === 1)
  const ubFinal = upperMatches.find(m => m.is_upper_final) || null

  const lbRound1 = lowerMatches.filter(m => m.round === 1)
  const lbRound2 = lowerMatches.filter(m => m.round === 2)
  const lbRound3 = lowerMatches.filter(m => m.round === 3)
  const lbFinal = lowerMatches.find(m => m.is_lower_final) || null

  // Calculate container height based on content
  const maxUpperCards = Math.max(ubRound1.length, ubFinal ? 1 : 0)
  const maxLowerCards = Math.max(lbRound1.length, lbRound2.length, lbRound3.length, lbFinal ? 1 : 0)
  const containerHeight = Math.max(
    (maxUpperCards - 1) * (CARD_H + V_GAP) + CARD_H,
    (maxLowerCards - 1) * (CARD_H + V_GAP) + CARD_H
  ) + (grandFinal ? CARD_H + V_GAP * 3 : 0)

  const matchById = (id?: string | null) => {
    if (!id) return null
    return [...upperMatches, ...lowerMatches, ...(grandFinal ? [grandFinal] : [])].find(m => m.id === id) || null
  }

  const getCenterX = (col: number, cardWidth: number = CARD_W) => {
    if (col === 0) return 0
    if (col === 1) return LOWER_COL_X
    return getGrandFinalX((LOWER_COL_X + CARD_W + H_GAP))
  }

  const getCenterY = (index: number, total: number) => {
    if (total <= 1) return 0
    const spacing = (containerHeight - CARD_H) / (total - 1)
    return spacing * index
  }

  const renderArrow = (fromMatch: BracketMatch | null, toMatch: BracketMatch | null, color: string, fromCol: number, toCol: number, fromIndex: number, toIndex: number, fromTotal: number, toTotal: number) => {
    if (!fromMatch || !toMatch) return null

    const x1 = getCenterX(fromCol) + CARD_W
    const y1 = getCenterY(fromIndex, fromTotal) + CARD_H / 2
    const x2 = getCenterX(toCol)
    const y2 = getCenterY(toIndex, toTotal) + CARD_H / 2

    const midX = (x1 + x2) / 2

    return (
      <path
        d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeDasharray="4 2"
        className="opacity-60"
      />
    )
  }

  const totalWidth = LOWER_COL_X + CARD_W + H_GAP
  const gfX = getGrandFinalX(totalWidth)

  // Upper bracket layout
  const ubY1 = getCenterY(0, ubRound1.length)
  const ubY2 = getCenterY(1, ubRound1.length)
  const ubFinalY = ubFinal ? getCenterY(0, 1) : 0
  const ubFinalX = getCenterX(0)

  // Lower bracket layout
  const lbY1 = getCenterY(0, lbRound1.length)
  const lbY2 = getCenterY(1, lbRound1.length)
  const lbY3 = getCenterY(0, lbRound2.length)
  const lbY4 = getCenterY(1, lbRound2.length)
  const lbY5 = lbRound3.length > 0 ? getCenterY(0, lbRound3.length) : 0
  const lbFinalY = lbFinal ? getCenterY(0, lbFinal ? 1 : 0) : 0

  // Grand final position
  const gfY = containerHeight - CARD_H - (grandFinal ? 0 : 999)

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[640px]">
        {/* Legend */}
        <div className="mb-4 flex flex-wrap items-center gap-4 text-xs text-gray-400">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-green-500"></div>
            <span>Upper Bracket</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-yellow-500"></div>
            <span>Lower Bracket</span>
          </div>
          {grandFinal && (
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-purple-500"></div>
              <span>Grand Final</span>
            </div>
          )}
        </div>

        {/* Bracket Tree */}
        <div className="relative" style={{ height: Math.max(containerHeight, gfY + CARD_H + 20) }}>
          {/* SVG Arrows Layer */}
          <svg className="absolute inset-0 w-full h-full" style={{ minWidth: totalWidth + 40, minHeight: Math.max(containerHeight, gfY + CARD_H + 20) }}>
            {/* Upper bracket arrows */}
            {ubRound1.length === 2 && ubFinal && (
              <>
                {/* Winner arrows from UB1 and UB2 to Upper Final */}
                {renderArrow(ubRound1[0], ubFinal, '#22c55e', 0, 0, 0, 0, ubRound1.length, 1)}
                {renderArrow(ubRound1[1], ubFinal, '#22c55e', 0, 0, 1, 0, ubRound1.length, 1)}
                {/* Loser arrows from UB1 and UB2 to Lower Bracket */}
                {lbRound2.length === 2 && (
                  <>
                    {renderArrow(ubRound1[0], lbRound2[0], '#eab308', 0, 1, 0, 0, ubRound1.length, lbRound2.length)}
                    {renderArrow(ubRound1[1], lbRound2[1], '#eab308', 0, 1, 1, 1, ubRound1.length, lbRound2.length)}
                  </>
                )}
              </>
            )}

            {/* Upper Final arrows */}
            {ubFinal && grandFinal && (
              <>
                {/* Winner to Grand Final */}
                {renderArrow(ubFinal, grandFinal, '#a855f7', 0, 2, 0, 0, 1, 1)}
                {/* Loser to Lower Final */}
                {lbFinal && renderArrow(ubFinal, lbFinal, '#eab308', 0, 1, 0, 0, 1, 1)}
              </>
            )}

            {/* Lower bracket round 1 arrows */}
            {lbRound1.length === 2 && lbRound2.length === 2 && (
              <>
                {renderArrow(lbRound1[0], lbRound2[0], '#eab308', 1, 1, 0, 0, lbRound1.length, lbRound2.length)}
                {renderArrow(lbRound1[1], lbRound2[1], '#eab308', 1, 1, 1, 1, lbRound1.length, lbRound2.length)}
              </>
            )}

            {/* Lower bracket round 2 arrows */}
            {lbRound2.length === 2 && lbRound3.length === 1 && (
              <>
                {renderArrow(lbRound2[0], lbRound3[0], '#eab308', 1, 1, 0, 0, lbRound2.length, lbRound3.length)}
                {renderArrow(lbRound2[1], lbRound3[0], '#eab308', 1, 1, 1, 0, lbRound2.length, lbRound3.length)}
              </>
            )}

            {/* Lower bracket round 3 to Lower Final */}
            {lbRound3.length === 1 && lbFinal && (
              renderArrow(lbRound3[0], lbFinal, '#eab308', 1, 1, 0, 0, lbRound3.length, 1)
            )}

            {/* Lower Final to Grand Final */}
            {lbFinal && grandFinal && (
              renderArrow(lbFinal, grandFinal, '#a855f7', 1, 2, 0, 0, 1, 1)
            )}
          </svg>

          {/* Match Cards Layer */}
          <div className="absolute inset-0">
            {/* Upper Bracket */}
            <div className={`transition-all duration-700 ${showUpper ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <div className="flex items-center gap-2 mb-2">
                <div className="h-3 w-3 rounded-full bg-green-500"></div>
                <h3 className="text-lg font-semibold text-green-300">Upper Bracket</h3>
              </div>
              <div className="relative" style={{ height: containerHeight }}>
                {ubRound1.map((match, idx) => (
                  <div
                    key={match.id}
                    className="absolute"
                    style={{
                      left: 0,
                      top: getCenterY(idx, ubRound1.length),
                      width: CARD_W,
                      height: CARD_H,
                    }}
                  >
                    <BracketMatchCard
                      match={match}
                      index={idx}
                      token={token}
                      tournamentId={tournamentId}
                      getTeamName={getTeamName}
                      onMatchUpdate={onMatchUpdate}
                      onAdvance={onAdvance}
                    />
                  </div>
                ))}
                {ubFinal && (
                  <div
                    className="absolute"
                    style={{
                      left: 0,
                      top: ubFinalY,
                      width: CARD_W,
                      height: CARD_H,
                    }}
                  >
                    <BracketMatchCard
                      match={ubFinal}
                      index={0}
                      isFinal
                      token={token}
                      tournamentId={tournamentId}
                      getTeamName={getTeamName}
                      onMatchUpdate={onMatchUpdate}
                      onAdvance={onAdvance}
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Lower Bracket */}
            <div className={`transition-all duration-700 ${showLower ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <div className="flex items-center gap-2 mb-2">
                <div className="h-3 w-3 rounded-full bg-yellow-500"></div>
                <h3 className="text-lg font-semibold text-yellow-300">Lower Bracket</h3>
              </div>
              <div className="relative" style={{ height: containerHeight, marginLeft: LOWER_COL_X }}>
                {lbRound1.map((match, idx) => (
                  <div
                    key={match.id}
                    className="absolute"
                    style={{
                      left: 0,
                      top: getCenterY(idx, lbRound1.length),
                      width: CARD_W,
                      height: CARD_H,
                    }}
                  >
                    <BracketMatchCard
                      match={match}
                      index={idx}
                      token={token}
                      tournamentId={tournamentId}
                      getTeamName={getTeamName}
                      onMatchUpdate={onMatchUpdate}
                      onAdvance={onAdvance}
                    />
                  </div>
                ))}
                {lbRound2.map((match, idx) => (
                  <div
                    key={match.id}
                    className="absolute"
                    style={{
                      left: 0,
                      top: getCenterY(idx, lbRound2.length),
                      width: CARD_W,
                      height: CARD_H,
                    }}
                  >
                    <BracketMatchCard
                      match={match}
                      index={idx}
                      token={token}
                      tournamentId={tournamentId}
                      getTeamName={getTeamName}
                      onMatchUpdate={onMatchUpdate}
                      onAdvance={onAdvance}
                    />
                  </div>
                ))}
                {lbRound3.map((match, idx) => (
                  <div
                    key={match.id}
                    className="absolute"
                    style={{
                      left: 0,
                      top: getCenterY(idx, lbRound3.length),
                      width: CARD_W,
                      height: CARD_H,
                    }}
                  >
                    <BracketMatchCard
                      match={match}
                      index={idx}
                      token={token}
                      tournamentId={tournamentId}
                      getTeamName={getTeamName}
                      onMatchUpdate={onMatchUpdate}
                      onAdvance={onAdvance}
                    />
                  </div>
                ))}
                {lbFinal && (
                  <div
                    className="absolute"
                    style={{
                      left: 0,
                      top: getCenterY(0, 1),
                      width: CARD_W,
                      height: CARD_H,
                    }}
                  >
                    <BracketMatchCard
                      match={lbFinal}
                      index={0}
                      isFinal
                      token={token}
                      tournamentId={tournamentId}
                      getTeamName={getTeamName}
                      onMatchUpdate={onMatchUpdate}
                      onAdvance={onAdvance}
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Grand Final */}
            {grandFinal && (
              <div
                className={`absolute transition-all duration-700 ${showGrandFinal ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}
                style={{
                  left: gfX,
                  top: gfY,
                  width: CARD_W,
                  height: CARD_H,
                }}
              >
                <div className="flex items-center justify-center gap-2 mb-2">
                  <div className="h-4 w-4 rounded-full bg-purple-500"></div>
                  <h3 className="text-xl font-bold text-purple-300">Grand Final (BO7)</h3>
                </div>
                <BracketMatchCard
                  match={grandFinal}
                  index={0}
                  isGrandFinal
                  token={token}
                  tournamentId={tournamentId}
                  getTeamName={getTeamName}
                  onMatchUpdate={onMatchUpdate}
                  onAdvance={onAdvance}
                />
              </div>
            )}
          </div>
        </div>

        {/* Empty state */}
        {upperMatches.length === 0 && lowerMatches.length === 0 && !grandFinal && (
          <div className="py-12 text-center">
            <p className="text-sm text-gray-400">Belum ada bracket. Klik "Generate Bracket" untuk membuat bracket.</p>
          </div>
        )}
      </div>
    </div>
  )
}
