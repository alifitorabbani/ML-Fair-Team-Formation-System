export interface Participant {
  player_id: string
  name?: string
  full_name?: string
  email?: string
  username?: string
  current_rank: string
  current_stars: number
  highest_rank: string
  highest_stars: number
  current_rank_score: number
  current_star_score: number
  highest_rank_score: number
  highest_star_score: number
  primary_lane: string
  secondary_lane?: string
  primary_lane_comfort: number
  secondary_lane_comfort?: number
  skill_score: number
  role_flexibility_score: number
  jungle_comfort: number
  exp_comfort: number
  mid_comfort: number
  gold_comfort: number
  roam_comfort: number
  lane_capabilities: Record<string, number>
  rank?: number
  status?: string
}

export interface LoginResponse {
  token: string
  player_id: string
  email: string
  username?: string
  full_name?: string
  name?: string
  role: 'admin' | 'user'
}

export interface SystemStateResponse {
  state: string
  current_ranking_version_id?: string
  current_team_version_id?: string
  updated_at?: string
}

export interface AdminDashboardStats {
  total_participants: number
  processed_participants: number
  qualified_count: number
  eliminated_count: number
  teams_generated: boolean
  total_teams: number
  payment_pending_count: number
  payment_verified_count: number
  payment_failed_count: number
  system_state: string
  ranking_generated: boolean
  team_generated: boolean
}

export interface PaymentResponse {
  id: string
  player_id: string
  status: string
  amount?: number
  method?: string
  paid_at?: string
  verified_by?: string
  verified_at?: string
  transaction_id?: string
  notes?: string
  created_at: string
  player_name?: string
  player_email?: string
  player_username?: string
  current_rank?: string
  current_stars?: number
  primary_lane?: string
}

export interface RankingVersionResponse {
  id: string
  generated_at: string
  confirmed_at?: string
  status: string
  total_participants: number
  qualified_count: number
  eliminated_count: number
  generated_by?: string
  is_active: boolean
}

export interface TeamVersionResponse {
  id: string
  ranking_version_id: string
  generated_at: string
  confirmed_at?: string
  status: string
  total_teams: number
  total_participants: number
  selected_count: number
  not_selected_count: number
  overall_fairness?: number
  random_seed?: number
  generated_by?: string
  is_active: boolean
}

export interface AuditLogResponse {
  id: string
  action: string
  actor?: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface TournamentResponse {
  id: string
  name: string
  description?: string
  timezone: string
  status: string
  third_place_mode: string
  selected_team_version_id?: string
  champion_team_id?: string
  runner_up_team_id?: string
  third_place_team_id?: string
  created_by?: string
  created_at: string
  updated_at: string
  finalized_at?: string
}

export interface TournamentDateResponse {
  id: string
  tournament_id: string
  date: string
  start_time: string
  end_time: string
  match_duration_minutes: number
  buffer_minutes: number
  min_rest_minutes: number
}

export interface TournamentTeamResponse {
  id: string
  tournament_id: string
  team_version_id: string
  team_id: string
  team_name_snapshot?: string
  seed?: number
}

export interface MatchResponse {
  id: string
  tournament_id: string
  stage: string
  group_id?: string
  bracket_id?: string
  round?: number
  match_number?: number
  scheduled_date: string
  start_time: string
  end_time: string
  team_a_id?: string
  team_b_id?: string
  format: string
  status: string
  score_a?: number
  score_b?: number
  kills_a?: number
  kills_b?: number
  deaths_a?: number
  deaths_b?: number
  winner_team_id?: string
  result_confidence?: number
  created_at: string
  updated_at: string
}

export interface StandingResponse {
  id: string
  group_id: string
  team_id: string
  rank?: number
  played: number
  win: number
  loss: number
  kill: number
  death: number
  kill_difference: number
  points: number
  computed_at: string
  is_manual_override: boolean
}

export interface BracketResponse {
  id: string
  tournament_id: string
  name: string
  bracket_type: string
  sort_order?: number
  rounds?: BracketRoundResponse[]
}

export interface BracketRoundResponse {
  id: string
  round_number: number
  round_name?: string
  slots: BracketSlotResponse[]
}

export interface BracketSlotResponse {
  id: string
  slot_number: number
  team_id?: string
  next_match_id?: string
  next_slot_number?: number
  status: string
}

export interface PlacementResponse {
  id: string
  tournament_id: string
  team_id: string
  placement: number
  source?: string
}

export interface ScheduleGenerateResponse {
  total_matches: number
  total_days: number
  min_rest_gap?: number
  avg_rest_gap?: number
  max_rest_gap?: number
  conflict_count: number
  constraint_violations: string[]
  fairness_score?: number
  warnings: string[]
  schedule: Record<string, any>[]
}

