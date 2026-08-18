import {
  TournamentResponse,
  TournamentDateResponse,
  TournamentTeamResponse,
  MatchResponse,
  StandingResponse,
  BracketResponse,
  PlacementResponse,
  ScheduleGenerateResponse,
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

export async function adminCreateTournament(token: string, data: any): Promise<TournamentResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create tournament')
  }
  return response.json()
}

export async function adminListTournaments(token: string): Promise<TournamentResponse[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch tournaments')
  }
  return response.json()
}

export async function adminGetTournament(token: string, tournamentId: string): Promise<TournamentResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    let errorMessage = 'Failed to fetch tournament'
    try {
      const error = await response.json()
      errorMessage = error.detail || errorMessage
    } catch {
      errorMessage = `Server error (${response.status})`
    }
    throw new Error(errorMessage)
  }
  return response.json()
}

export async function adminUpdateTournament(token: string, tournamentId: string, data: any): Promise<TournamentResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update tournament')
  }
  return response.json()
}

export async function adminDeleteTournament(token: string, tournamentId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}`, {
    method: 'DELETE',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to delete tournament')
  }
}

export async function adminSelectTeams(token: string, tournamentId: string, teamVersionId: string, teamIds: string[]): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/teams`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify({ team_version_id: teamVersionId, team_ids: teamIds }),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to select teams')
  }
  return response.json()
}

export async function adminGetTournamentTeams(token: string, tournamentId: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/teams`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch tournament teams')
  }
  return response.json()
}

export async function adminGetAvailableTeams(token: string, tournamentId: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/available-teams`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch available teams')
  }
  return response.json()
}

export async function adminAutoAssignGroups(token: string, tournamentId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/groups/auto-assign`, {
    method: 'POST',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to auto assign groups')
  }
  return response.json()
}

export async function adminCreateGroup(token: string, tournamentId: string, data: any): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/groups`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create group')
  }
  return response.json()
}

export async function adminUpdateGroup(token: string, tournamentId: string, groupId: string, data: any): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/groups/${encodeURIComponent(groupId)}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update group')
  }
  return response.json()
}

export async function adminGetGroups(token: string, tournamentId: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/groups`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch groups')
  }
  return response.json()
}

export async function adminClearGroups(token: string, tournamentId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/groups/clear`, {
    method: 'POST',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to clear groups')
  }
  return response.json()
}

export async function adminGenerateSchedule(token: string, tournamentId: string, config?: { start_date?: string; end_date?: string; match_duration_minutes?: number; bo_format?: string; min_rest_minutes?: number; buffer_minutes?: number }): Promise<ScheduleGenerateResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/schedule/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(config || {}),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to generate schedule')
  }
  return response.json()
}

export async function adminGetSchedule(token: string, tournamentId: string): Promise<MatchResponse[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/schedule`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch schedule')
  }
  return response.json()
}

export async function adminCreateMatch(token: string, tournamentId: string, data: any): Promise<MatchResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/matches`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create match')
  }
  return response.json()
}

export async function adminUpdateMatch(token: string, tournamentId: string, matchId: string, data: any): Promise<MatchResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/matches/${encodeURIComponent(matchId)}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update match')
  }
  return response.json()
}

export async function adminDeleteMatch(token: string, tournamentId: string, matchId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/matches/${encodeURIComponent(matchId)}`, {
    method: 'DELETE',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to delete match')
  }
}

export async function adminSubmitMatchResult(token: string, tournamentId: string, matchId: string, data: { score_a: number; score_b: number; kills_a?: number; kills_b?: number; deaths_a?: number; deaths_b?: number; winner_team_id?: string; loser_team_id?: string; change_reason?: string; map_results?: Array<{ map_number: number; team_a_id?: string; team_b_id?: string; score_a?: number; score_b?: number; kills_a?: number; kills_b?: number; deaths_a?: number; deaths_b?: number; winner_team_id?: string; status?: string }> }): Promise<MatchResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/matches/${encodeURIComponent(matchId)}/result`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to submit result')
  }
  return response.json()
}

export async function adminSubmitGameResult(token: string, tournamentId: string, matchId: string, gameNumber: number, data: { map_number: number; team_a_id?: string; team_b_id?: string; score_a?: number; score_b?: number; kills_a?: number; kills_b?: number; deaths_a?: number; deaths_b?: number; winner_team_id?: string; status?: string; scheduled_date?: string; start_time?: string; end_time?: string }): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/matches/${encodeURIComponent(matchId)}/game/${gameNumber}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to submit game result')
  }
  return response.json()
}

export async function adminConfirmMatchResult(token: string, tournamentId: string, matchId: string): Promise<MatchResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/matches/${encodeURIComponent(matchId)}/result/confirm`, {
    method: 'POST',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to confirm result')
  }
  return response.json()
}

export async function adminGetStandings(token: string, tournamentId: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/standings`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch standings')
  }
  return response.json()
}

export async function adminGetDailyStandings(token: string, tournamentId: string, matchDate: string, groupId?: string): Promise<any> {
  const url = new URL(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/standings/daily`)
  url.searchParams.set('match_date', matchDate)
  if (groupId) url.searchParams.set('group_id', groupId)
  const response = await fetch(url.toString(), {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch daily standings')
  }
  return response.json()
}

export async function userGetDailyStandings(token: string, tournamentId: string, matchDate: string, groupId?: string): Promise<any> {
  const url = new URL(`${API_BASE}/api/tournaments/${encodeURIComponent(tournamentId)}/standings/daily`)
  url.searchParams.set('match_date', matchDate)
  if (groupId) url.searchParams.set('group_id', groupId)
  const response = await fetch(url.toString(), {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch daily standings')
  }
  return response.json()
}

export async function adminOverrideStandings(token: string, tournamentId: string, data: any[]): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/standings/override`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to override standings')
  }
  return response.json()
}

export async function adminRecalculateStandings(token: string, tournamentId: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/standings/recalculate`, {
    method: 'POST',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to recalculate standings')
  }
  return response.json()
}

export async function adminGenerateKnockout(token: string, tournamentId: string, qualifiedTeamIds: string[], populateMatches: boolean = true): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/knockout/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify({ qualified_team_ids: qualifiedTeamIds, populate_matches: populateMatches }),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to generate knockout')
  }
  return response.json()
}

export async function adminResolveKnockout(token: string, tournamentId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/knockout/resolve`, {
    method: 'POST',
    headers: {
      'X-User-Token': token,
    },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to resolve knockout')
  }
  return response.json()
}

export async function adminResetBracket(token: string, tournamentId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/knockout/reset`, {
    method: 'POST',
    headers: {
      'X-User-Token': token,
    },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to reset bracket')
  }
  return response.json()
}

export async function adminGetKnockout(token: string, tournamentId: string): Promise<BracketResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/knockout`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch knockout')
  }
  return response.json()
}

export async function adminAdvanceKnockout(token: string, tournamentId: string, matchId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/knockout/${encodeURIComponent(matchId)}/advance`, {
    method: 'POST',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to advance knockout')
  }
  return response.json()
}

export async function adminSetBracketQualification(token: string | null, tournamentId: string, data: { team_id: string; bracket_type: string; group_id?: string; rank?: number }): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/bracket-qualifications`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'X-User-Token': token } : {}),
    },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to set bracket qualification')
  }
  return response.json()
}

export async function adminGetBracketQualifications(token: string | null, tournamentId: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/bracket-qualifications`, {
    headers: {
      ...(token ? { 'X-User-Token': token } : {}),
    },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch bracket qualifications')
  }
  return response.json()
}

export async function adminClearBracketQualifications(token: string | null, tournamentId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/bracket-qualifications`, {
    method: 'DELETE',
    headers: {
      ...(token ? { 'X-User-Token': token } : {}),
    },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to clear bracket qualifications')
  }
  return response.json()
}

export async function adminSetPlacement(token: string, tournamentId: string, teamId: string, placement: number, source?: string): Promise<PlacementResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/placements/${encodeURIComponent(teamId)}?placement=${placement}${source ? `&source=${encodeURIComponent(source)}` : ''}`, {
    method: 'POST',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to set placement')
  }
  return response.json()
}

export async function adminFinalizeChampion(token: string, tournamentId: string): Promise<TournamentResponse> {
  const response = await fetch(`${API_BASE}/api/admin/tournaments/${encodeURIComponent(tournamentId)}/champion/finalize`, {
    method: 'POST',
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to finalize champion')
  }
  return response.json()
}

export async function userListTournaments(token: string): Promise<TournamentResponse[]> {
  const response = await fetch(`${API_BASE}/api/tournaments`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch tournaments')
  }
  return response.json()
}

export async function userGetTournament(token: string, tournamentId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/tournaments/${encodeURIComponent(tournamentId)}`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch tournament')
  }
  return response.json()
}

export async function userGetSchedule(token: string, tournamentId: string): Promise<MatchResponse[]> {
  const response = await fetch(`${API_BASE}/api/tournaments/${encodeURIComponent(tournamentId)}/schedule`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch schedule')
  }
  return response.json()
}

export async function userGetMatches(token: string, tournamentId: string): Promise<MatchResponse[]> {
  const response = await fetch(`${API_BASE}/api/tournaments/${encodeURIComponent(tournamentId)}/matches`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch matches')
  }
  return response.json()
}

export async function userGetStandings(token: string, tournamentId: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/tournaments/${encodeURIComponent(tournamentId)}/standings`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch standings')
  }
  return response.json()
}

export async function userGetKnockout(token: string, tournamentId: string): Promise<BracketResponse> {
  const response = await fetch(`${API_BASE}/api/tournaments/${encodeURIComponent(tournamentId)}/knockout`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch knockout')
  }
  return response.json()
}

export async function userGetResults(token: string, tournamentId: string): Promise<MatchResponse[]> {
  const response = await fetch(`${API_BASE}/api/tournaments/${encodeURIComponent(tournamentId)}/results`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch results')
  }
  return response.json()
}

export async function userGetPlacements(token: string, tournamentId: string): Promise<PlacementResponse[]> {
  const response = await fetch(`${API_BASE}/api/tournaments/${encodeURIComponent(tournamentId)}/placements`, {
    headers: { 'X-User-Token': token },
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch placements')
  }
  return response.json()
}
