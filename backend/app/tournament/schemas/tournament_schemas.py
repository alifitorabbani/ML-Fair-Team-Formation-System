from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
from enum import Enum


class TournamentStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    CONFIGURED = "CONFIGURED"
    TEAMS_LOCKED = "TEAMS_LOCKED"
    GROUPS_CONFIGURED = "GROUPS_CONFIGURED"
    SCHEDULE_GENERATED = "SCHEDULE_GENERATED"
    GROUP_STAGE = "GROUP_STAGE"
    GROUP_FINALIZED = "GROUP_FINALIZED"
    KNOCKOUT = "KNOCKOUT"
    FINAL = "FINAL"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MatchStageEnum(str, Enum):
    GROUP_STAGE = "GROUP_STAGE"
    KNOCKOUT = "KNOCKOUT"


class MatchStatusEnum(str, Enum):
    SCHEDULED = "SCHEDULED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BracketTypeEnum(str, Enum):
    UPPER = "UPPER"
    MIDDLE = "MIDDLE"
    LOWER = "LOWER"


class ThirdPlaceModeEnum(str, Enum):
    DISABLED = "DISABLED"
    THIRD_PLACE_MATCH = "THIRD_PLACE_MATCH"
    BRACKET_BASED = "BRACKET_BASED"
    MANUAL = "MANUAL"


class BOFormatEnum(str, Enum):
    BO1 = "BO1"
    BO3 = "BO3"
    BO5 = "BO5"
    BO7 = "BO7"


class BracketLoserRuleEnum(str, Enum):
    TO_MIDDLE = "TO_MIDDLE"
    TO_LOWER = "TO_LOWER"
    ELIMINATED = "ELIMINATED"


class TournamentDateConfig(BaseModel):
    date: date
    start_time: time
    end_time: time
    match_duration_minutes: int = 45
    buffer_minutes: int = 0
    min_rest_minutes: int = 60


class TournamentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    timezone: str = "Asia/Jakarta"
    dates: List[TournamentDateConfig]
    bo_formats: List[str] = Field(default_factory=lambda: ["BO1", "BO3", "BO5"])
    match_duration_minutes: int = 45
    buffer_minutes: int = 0
    min_rest_minutes: int = 60
    group_count: int = Field(ge=1, le=16, default=4)
    teams_per_group: int = Field(ge=2, le=8, default=4)
    qualification_count: int = Field(ge=1, le=4, default=2)
    knockout_brackets: List[str] = Field(default_factory=lambda: ["UPPER"])
    upper_loser_rule: str = "ELIMINATED"
    middle_loser_rule: str = "ELIMINATED"
    third_place_mode: ThirdPlaceModeEnum = ThirdPlaceModeEnum.DISABLED
    tie_breaker: List[str] = Field(default_factory=lambda: ["points", "win", "kill_difference", "kill", "death"])


class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    timezone: Optional[str] = None
    status: Optional[TournamentStatusEnum] = None
    config_json: Optional[Dict[str, Any]] = None
    group_config_json: Optional[Dict[str, Any]] = None
    knockout_config_json: Optional[Dict[str, Any]] = None
    third_place_mode: Optional[ThirdPlaceModeEnum] = None
    champion_team_id: Optional[str] = None
    runner_up_team_id: Optional[str] = None
    third_place_team_id: Optional[str] = None


class TournamentTeamSelect(BaseModel):
    team_version_id: str
    team_ids: List[str]


class TournamentGroupCreate(BaseModel):
    name: str
    team_ids: List[str]
    sort_order: Optional[int] = None


class TournamentGroupUpdate(BaseModel):
    name: Optional[str] = None
    team_ids: Optional[List[str]] = None
    sort_order: Optional[int] = None


class MatchCreate(BaseModel):
    scheduled_date: date
    start_time: time
    end_time: time
    team_a_id: Optional[str] = None
    team_b_id: Optional[str] = None
    format: BOFormatEnum = BOFormatEnum.BO1
    stage: MatchStageEnum = MatchStageEnum.GROUP_STAGE
    group_id: Optional[str] = None
    bracket_id: Optional[str] = None
    round: Optional[int] = None
    match_number: Optional[int] = None


class MatchUpdate(BaseModel):
    scheduled_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    team_a_id: Optional[str] = None
    team_b_id: Optional[str] = None
    format: Optional[BOFormatEnum] = None
    status: Optional[MatchStatusEnum] = None


class BracketMatchMapSubmit(BaseModel):
    map_number: int
    team_a_id: Optional[str] = None
    team_b_id: Optional[str] = None
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    kills_a: Optional[int] = None
    kills_b: Optional[int] = None
    deaths_a: Optional[int] = None
    deaths_b: Optional[int] = None
    winner_team_id: Optional[str] = None
    status: Optional[str] = None


class BracketMatchMapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    match_id: str
    map_number: int
    team_a_id: Optional[str] = None
    team_b_id: Optional[str] = None
    winner_team_id: Optional[str] = None
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    kills_a: Optional[int] = None
    kills_b: Optional[int] = None
    deaths_a: Optional[int] = None
    deaths_b: Optional[int] = None
    status: str
    scheduled_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    created_at: Optional[datetime] = None


class MatchResultSubmit(BaseModel):
    score_a: int
    score_b: int
    kills_a: Optional[int] = None
    kills_b: Optional[int] = None
    deaths_a: Optional[int] = None
    deaths_b: Optional[int] = None
    winner_team_id: Optional[str] = None
    loser_team_id: Optional[str] = None
    change_reason: Optional[str] = None
    map_results: Optional[List[BracketMatchMapSubmit]] = None


class MatchResultOCRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    team_a_name: Optional[str] = None
    team_b_name: Optional[str] = None
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    kills_a: Optional[int] = None
    kills_b: Optional[int] = None
    deaths_a: Optional[int] = None
    deaths_b: Optional[int] = None
    winner_team_id: Optional[str] = None
    confidence: float = 0.0
    is_valid: bool = False
    validation_message: Optional[str] = None
    raw_text: Optional[str] = None


class BracketQualificationCreate(BaseModel):
    group_id: Optional[str] = None
    team_id: str
    bracket_type: str
    rank: Optional[int] = None


class ScheduleConfig(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    match_duration_minutes: int = 45
    bo_format: str = "BO1"
    min_rest_minutes: int = 60
    buffer_minutes: int = 0


class StandingsOverride(BaseModel):
    team_id: str
    rank: Optional[int] = None
    played: Optional[int] = None
    win: Optional[int] = None
    loss: Optional[int] = None
    kill: Optional[int] = None
    death: Optional[int] = None
    kill_difference: Optional[int] = None
    points: Optional[int] = None
    reason: Optional[str] = None


class BracketGenerateRequest(BaseModel):
    qualified_team_ids: List[str]
    seeding: List[str]
    bracket_type: str


class PlacementSet(BaseModel):
    team_id: str
    placement: int
    source: Optional[str] = None


class TournamentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    timezone: str
    status: str
    third_place_mode: str
    selected_team_version_id: Optional[str] = None
    champion_team_id: Optional[str] = None
    runner_up_team_id: Optional[str] = None
    third_place_team_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None


class TournamentDateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    date: date
    start_time: time
    end_time: time
    match_duration_minutes: int
    buffer_minutes: int
    min_rest_minutes: int


class TournamentTeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    team_version_id: str
    team_id: str
    team_name_snapshot: Optional[str] = None
    seed: Optional[int] = None


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    name: str
    sort_order: Optional[int] = None


class GroupMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_id: str
    tournament_team_id: str
    seed: Optional[int] = None


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    stage: str
    group_id: Optional[str] = None
    bracket_id: Optional[str] = None
    round: Optional[int] = None
    match_number: Optional[int] = None
    scheduled_date: date
    start_time: time
    end_time: time
    team_a_id: Optional[str] = None
    team_b_id: Optional[str] = None
    format: str
    status: str
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    kills_a: Optional[int] = None
    kills_b: Optional[int] = None
    deaths_a: Optional[int] = None
    deaths_b: Optional[int] = None
    winner_team_id: Optional[str] = None
    result_confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class StandingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_id: str
    team_id: str
    rank: Optional[int] = None
    played: int
    win: int
    loss: int
    kill: int
    death: int
    kill_difference: int
    points: int
    computed_at: datetime
    is_manual_override: bool


class BracketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    name: str
    bracket_type: str
    sort_order: Optional[int] = None


class BracketSlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    round_id: str
    slot_number: int
    team_id: Optional[str] = None
    next_match_id: Optional[str] = None
    next_slot_number: Optional[int] = None
    status: str


class PlacementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    team_id: str
    placement: int
    source: Optional[str] = None


class ScheduleGenerateResponse(BaseModel):
    total_matches: int
    total_days: int
    min_rest_gap: Optional[float] = None
    avg_rest_gap: Optional[float] = None
    max_rest_gap: Optional[float] = None
    conflict_count: int
    constraint_violations: List[str]
    fairness_score: Optional[float] = None
    warnings: List[str]
    schedule: List[Dict[str, Any]]
