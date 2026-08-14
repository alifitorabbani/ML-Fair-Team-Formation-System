from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, create_engine
from sqlalchemy.orm import declarative_base
from datetime import datetime
import json
from uuid import uuid4

Base = declarative_base()


def uuid_str():
    return str(uuid4())


class ParticipantDB(Base):
    __tablename__ = "participants"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    username = Column(String, nullable=True)
    current_rank = Column(String, nullable=False)
    current_stars = Column(Integer, nullable=False)
    highest_rank = Column(String, nullable=False)
    highest_stars = Column(Integer, nullable=False)
    primary_lane = Column(String, nullable=False)
    primary_lane_comfort = Column(Integer, nullable=False)
    secondary_lane = Column(String, nullable=True)
    secondary_lane_comfort = Column(Integer, nullable=True)
    skill_score = Column(Float, nullable=True)
    current_rank_score = Column(Float, nullable=True)
    current_star_score = Column(Float, nullable=True)
    highest_rank_score = Column(Float, nullable=True)
    highest_star_score = Column(Float, nullable=True)
    role_flexibility_score = Column(Float, nullable=True)
    jungle_comfort = Column(Float, nullable=True)
    exp_comfort = Column(Float, nullable=True)
    mid_comfort = Column(Float, nullable=True)
    gold_comfort = Column(Float, nullable=True)
    roam_comfort = Column(Float, nullable=True)
    lane_capabilities = Column(String, nullable=True)
    status = Column(String, nullable=False, default="REGISTERED")
    rank = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionDB(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    random_seed = Column(Integer, nullable=False)
    total_participants = Column(Integer, nullable=False)
    total_teams = Column(Integer, nullable=False)
    selected_count = Column(Integer, nullable=False)
    not_selected_count = Column(Integer, nullable=False)
    overall_fairness = Column(Float, nullable=False)
    optimization_iterations = Column(Integer, nullable=False)
    processing_time_ms = Column(Float, nullable=False)
    results_json = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RankingVersion(Base):
    __tablename__ = "ranking_versions"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="DRAFT")
    total_participants = Column(Integer, nullable=False)
    qualified_count = Column(Integer, nullable=False)
    eliminated_count = Column(Integer, nullable=False)
    generated_by = Column(String, nullable=True)
    seed = Column(Integer, nullable=True)
    score_components = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class TeamVersion(Base):
    __tablename__ = "team_versions"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    ranking_version_id = Column(String, nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="DRAFT")
    total_teams = Column(Integer, nullable=False)
    total_participants = Column(Integer, nullable=False)
    selected_count = Column(Integer, nullable=False)
    not_selected_count = Column(Integer, nullable=False)
    overall_fairness = Column(Float, nullable=True)
    random_seed = Column(Integer, nullable=True)
    optimization_iterations = Column(Integer, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    generated_by = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    team_version_id = Column(String, nullable=False, index=True)
    team_id = Column(String, nullable=False)
    player_id = Column(String, nullable=False, index=True)
    assigned_lane = Column(String, nullable=False)
    comfort_in_assigned_lane = Column(Integer, nullable=True)
    role_compatibility_score = Column(Float, nullable=True)
    assignment_reason = Column(String, nullable=True)
    average_skill_score = Column(Float, nullable=True)
    role_balance_score = Column(Float, nullable=True)
    overall_fairness = Column(Float, nullable=True)
    fairness_breakdown = Column(String, nullable=True)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    player_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="PENDING")
    amount = Column(Float, nullable=True)
    method = Column(String, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    transaction_id = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemState(Base):
    __tablename__ = "system_state"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    state = Column(String, nullable=False, default="DRAFT")
    current_ranking_version_id = Column(String, nullable=True)
    current_team_version_id = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    action = Column(String, nullable=False, index=True)
    actor = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    log_metadata = Column(String, nullable=True)
