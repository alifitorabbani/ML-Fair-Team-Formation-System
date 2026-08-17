'use client'

import { useState, useEffect } from 'react'

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
}

interface BracketProps {
  upperMatches: BracketMatch[]
  lowerMatches: BracketMatch[]
  grandFinal: BracketMatch | null
}

function BracketMatchCard({ match, index, isFinal, isGrandFinal }: { match: BracketMatch; index: number; isFinal?: boolean; isGrandFinal?: boolean }) {
  const [animated, setAnimated] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), index * 100)
    return () => clearTimeout(timer)
  }, [index])

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

  return (
    <div
      className={`rounded-xl border p-3 transition-all duration-500 ${getBorderColor()} ${animated ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'}`}
    >
      <div className="mb-1 text-xs text-gray-400">
        {isGrandFinal ? 'Final' : isFinal ? 'Final' : `Round ${match.round}`}
        {match.format && <span className="ml-2 text-gray-500">({match.format})</span>}
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
      {match.status === 'COMPLETED' && match.winner_team_id && (
        <div className="mt-2 text-xs text-green-400">
          Winner: {match.winner_team_id}
        </div>
      )}
    </div>
  )
}

export default function AnimatedBracket({ upperMatches, lowerMatches, grandFinal }: BracketProps) {
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
            />
          </div>
        </div>
      )}
    </div>
  )
}
