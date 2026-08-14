from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class RankEnum(str, Enum):
    warrior = "Warrior"
    elite = "Elite"
    master = "Master"
    grandmaster = "Grandmaster"
    epic = "Epic"
    legend = "Legend"
    mythic = "Mythic"
    mythical_honor = "Mythical Honor"
    mythical_glory = "Mythical Glory"
    mythical_immortal = "Mythical Immortal"


class LaneEnum(str, Enum):
    exp = "EXP Lane"
    jungle = "Jungle"
    mid = "Mid Lane"
    gold = "Gold Lane"
    roam = "Roam"


class ParticipantStatus(str, Enum):
    registered = "REGISTERED"
    ranked = "RANKED"
    qualified = "QUALIFIED"
    eliminated = "ELIMINATED"
    payment_pending = "PAYMENT_PENDING"
    payment_verified = "PAYMENT_VERIFIED"
    team_assigned = "TEAM_ASSIGNED"


class PaymentStatus(str, Enum):
    pending = "PENDING"
    paid = "PAID"
    failed = "FAILED"


class SystemState(str, Enum):
    draft = "DRAFT"
    ranking_generated = "RANKING_GENERATED"
    team_generated = "TEAM_GENERATED"
    payment_open = "PAYMENT_OPEN"
    competition_ready = "COMPETITION_READY"


class RankingStatus(str, Enum):
    draft = "DRAFT"
    confirmed = "CONFIRMED"


class TeamStatus(str, Enum):
    draft = "DRAFT"
    confirmed = "CONFIRMED"


class ValidationError(BaseModel):
    row: int
    field: str
    message: str
    value: Optional[str] = None


class CSVValidationResult(BaseModel):
    total_rows: int
    valid_participants: int
    invalid_participants: int
    missing_fields: List[ValidationError]
    invalid_records: List[ValidationError]
    duplicate_records: List[ValidationError]
    is_valid: bool


class ParticipantInput(BaseModel):
    player_id: str
    name: Optional[str] = None
    current_rank: str
    current_stars: int
    highest_rank: str
    highest_stars: int
    primary_lane: str
    primary_lane_comfort: int
    secondary_lane: Optional[str] = None
    secondary_lane_comfort: Optional[int] = None


class ParticipantFeatures(BaseModel):
    player_id: str
    name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    current_rank: str
    current_stars: int
    highest_rank: str
    highest_stars: int
    current_rank_score: float
    current_star_score: float
    highest_rank_score: float
    highest_star_score: float
    primary_lane: str
    secondary_lane: Optional[str]
    primary_lane_comfort: int
    secondary_lane_comfort: Optional[int]
    skill_score: float
    skill_score_breakdown: Optional[Dict[str, float]] = None
    role_flexibility_score: float
    role_flexibility_breakdown: Optional[Dict[str, float]] = None
    jungle_comfort: float
    exp_comfort: float
    mid_comfort: float
    gold_comfort: float
    roam_comfort: float
    lane_capabilities: Dict[str, float]
    rank: Optional[int] = None
    ranking_details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class RankingResponse(BaseModel):
    rankings: List[ParticipantFeatures]
    total: int
    generated_at: str
    score_components: Optional[Dict[str, Any]] = None
    qualified_count: int = 0
    eliminated_count: int = 0


class RankingPreviewResponse(BaseModel):
    rankings: List[ParticipantFeatures]
    total: int
    qualified_count: int
    eliminated_count: int
    score_components: Optional[Dict[str, Any]] = None
    preview_generated_at: str


class TeamPlayer(BaseModel):
    player_id: str
    name: Optional[str]
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    assigned_lane: str
    current_rank: str
    current_stars: int
    highest_rank: str
    highest_stars: int
    primary_lane: str
    secondary_lane: Optional[str]
    primary_lane_comfort: int
    secondary_lane_comfort: Optional[int]
    comfort_in_assigned_lane: int
    skill_score: float
    assignment_reason: Optional[str] = None
    role_compatibility_score: Optional[float] = None


class TeamResult(BaseModel):
    team_id: str
    players: List[TeamPlayer]
    average_skill_score: float
    role_balance_score: float
    comfort_score: float
    overall_fairness: float
    fairness_breakdown: Optional[Dict[str, Any]] = None


class ParticipantSelection(BaseModel):
    selected: List[ParticipantFeatures]
    not_selected: List[ParticipantFeatures]
    selection_reason: str


class OptimizationResult(BaseModel):
    selected_participants: List[ParticipantFeatures]
    not_selected: List[ParticipantFeatures]
    teams: List[TeamResult]
    total_participants: int
    total_teams: int
    selected_count: int
    not_selected_count: int
    random_seed: int
    overall_fairness: float
    optimization_iterations: int
    processing_time_ms: float


class ProcessingStatus(BaseModel):
    step: str
    status: str
    message: Optional[str] = None


class ProcessRequest(BaseModel):
    random_seed: Optional[int] = None
    min_fairness_threshold: Optional[float] = None
    max_iterations: Optional[int] = None
    team_size: Optional[int] = None


class CompatibilityUpdateRequest(BaseModel):
    from_role: str
    to_role: str
    value: float


class ExportFormat(str, Enum):
    csv = "csv"
    excel = "excel"


class RoleHistoryResponse(BaseModel):
    player_id: str
    role_distribution: Dict[str, int]


class PairingHistoryResponse(BaseModel):
    pair: str
    count: int


class LoginRequest(BaseModel):
    email: str


class AdminGenerateRankingRequest(BaseModel):
    confirm: bool = False


class AdminGenerateTeamRequest(BaseModel):
    confirm: bool = False
    random_seed: Optional[int] = None


class PaymentVerificationRequest(BaseModel):
    player_id: str
    status: PaymentStatus
    transaction_id: Optional[str] = None
    notes: Optional[str] = None


class SystemStateResponse(BaseModel):
    state: str
    current_ranking_version_id: Optional[str] = None
    current_team_version_id: Optional[str] = None
    updated_at: Optional[str] = None


class RankingVersionResponse(BaseModel):
    id: str
    generated_at: str
    confirmed_at: Optional[str] = None
    status: str
    total_participants: int
    qualified_count: int
    eliminated_count: int
    generated_by: Optional[str] = None
    is_active: bool


class TeamVersionResponse(BaseModel):
    id: str
    ranking_version_id: str
    generated_at: str
    confirmed_at: Optional[str] = None
    status: str
    total_teams: int
    total_participants: int
    selected_count: int
    not_selected_count: int
    overall_fairness: Optional[float] = None
    random_seed: Optional[int] = None
    generated_by: Optional[str] = None
    is_active: bool


class PaymentResponse(BaseModel):
    id: str
    player_id: str
    status: str
    amount: Optional[float] = None
    method: Optional[str] = None
    paid_at: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class AuditLogResponse(BaseModel):
    id: str
    action: str
    actor: Optional[str] = None
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class AdminDashboardStats(BaseModel):
    total_participants: int
    processed_participants: int
    qualified_count: int
    eliminated_count: int
    teams_generated: bool
    total_teams: int
    payment_pending_count: int
    payment_verified_count: int
    payment_failed_count: int
    system_state: str
    ranking_generated: bool
    team_generated: bool
