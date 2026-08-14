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
