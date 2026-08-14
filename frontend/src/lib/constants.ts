export const LANE_COLORS: Record<string, string> = {
  Jungle: 'bg-green-500',
  'EXP Lane': 'bg-red-500',
  'Mid Lane': 'bg-blue-500',
  'Gold Lane': 'bg-yellow-500',
  Roam: 'bg-purple-500',
}

export const LANE_ICONS: Record<string, string> = {
  Jungle: '🌿',
  'EXP Lane': '⚔️',
  'Mid Lane': '🔮',
  'Gold Lane': '💰',
  Roam: '🛡️',
}

export const RANK_TIER_ORDER = [
  'Mythical Immortal',
  'Mythical Glory',
  'Mythical Honor',
  'Mythic',
  'Legend',
  'Epic',
  'Grandmaster',
  'Master',
  'Elite',
  'Warrior',
] as const

export const RANK_TIER_COLORS: Record<string, string> = {
  'Mythical Immortal': 'text-brand-400',
  'Mythical Glory': 'text-orange-400',
  'Mythical Honor': 'text-amber-400',
  Mythic: 'text-yellow-400',
  Legend: 'text-green-400',
  Epic: 'text-blue-400',
  Grandmaster: 'text-purple-400',
  Master: 'text-pink-400',
  Elite: 'text-gray-400',
  Warrior: 'text-gray-500',
}

export const SYSTEM_STATE_LABEL: Record<string, { label: string; color: string }> = {
  DRAFT: { label: 'Draft', color: 'bg-gray-500/20 text-gray-300 border-gray-500/30' },
  RANKING_GENERATED: { label: 'Ranking Generated', color: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
  RANKING_CONFIRMED: { label: 'Ranking Confirmed', color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
  TEAM_GENERATED: { label: 'Team Generated', color: 'bg-brand-500/20 text-brand-300 border-brand-500/30' },
  PAYMENT_OPEN: { label: 'Payment Open', color: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
  COMPETITION_READY: { label: 'Competition Ready', color: 'bg-green-500/20 text-green-300 border-green-500/30' },
}
