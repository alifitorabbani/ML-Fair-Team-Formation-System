from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Date, Time, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from uuid import uuid4

from app.models.models import Base

def uuid_str():
    return str(uuid4())


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    timezone = Column(String, nullable=False, default="Asia/Jakarta")
    status = Column(String, nullable=False, default="DRAFT", index=True)
    config_json = Column(Text, nullable=True)
    group_config_json = Column(Text, nullable=True)
    knockout_config_json = Column(Text, nullable=True)
    third_place_mode = Column(String, nullable=False, default="DISABLED")
    selected_team_version_id = Column(String, nullable=True, index=True)
    champion_team_id = Column(String, nullable=True)
    runner_up_team_id = Column(String, nullable=True)
    third_place_team_id = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at = Column(DateTime, nullable=True)

    dates = relationship("TournamentDate", back_populates="tournament", cascade="all, delete-orphan")
    teams = relationship("TournamentTeam", back_populates="tournament", cascade="all, delete-orphan")
    groups = relationship("TournamentGroup", back_populates="tournament", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="tournament", cascade="all, delete-orphan")
    brackets = relationship("KnockoutBracket", back_populates="tournament", cascade="all, delete-orphan")
    schedule_versions = relationship("ScheduleVersion", back_populates="tournament", cascade="all, delete-orphan")
    placements = relationship("TournamentPlacement", back_populates="tournament", cascade="all, delete-orphan")
    bracket_qualifications = relationship("BracketQualification", back_populates="tournament", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("name", name="uq_tournament_name"),
    )


class TournamentDate(Base):
    __tablename__ = "tournament_dates"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    match_duration_minutes = Column(Integer, nullable=False, default=45)
    buffer_minutes = Column(Integer, nullable=False, default=0)
    min_rest_minutes = Column(Integer, nullable=False, default=60)

    tournament = relationship("Tournament", back_populates="dates")

    __table_args__ = (
        UniqueConstraint("tournament_id", "date", name="uq_tournament_date"),
    )


class TournamentTeam(Base):
    __tablename__ = "tournament_teams"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    team_version_id = Column(String, nullable=False, index=True)
    team_id = Column(String, nullable=False, index=True)
    team_name_snapshot = Column(String, nullable=True)
    seed = Column(Integer, nullable=True)

    tournament = relationship("Tournament", back_populates="teams")
    group_members = relationship("TournamentGroupMember", back_populates="tournament_team", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tournament_id", "team_id", name="uq_tournament_team"),
    )


class TournamentGroup(Base):
    __tablename__ = "tournament_groups"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=True)

    tournament = relationship("Tournament", back_populates="groups")
    members = relationship("TournamentGroupMember", back_populates="group", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="group")

    __table_args__ = (
        UniqueConstraint("tournament_id", "name", name="uq_tournament_group_name"),
    )


class TournamentGroupMember(Base):
    __tablename__ = "tournament_group_members"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    group_id = Column(String, ForeignKey("tournament_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    tournament_team_id = Column(String, ForeignKey("tournament_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    seed = Column(Integer, nullable=True)

    group = relationship("TournamentGroup", back_populates="members")
    tournament_team = relationship("TournamentTeam", back_populates="group_members")

    __table_args__ = (
        UniqueConstraint("group_id", "tournament_team_id", name="uq_group_team"),
    )


class Match(Base):
    __tablename__ = "matches"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String, nullable=False, default="GROUP_STAGE", index=True)
    group_id = Column(String, ForeignKey("tournament_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    bracket_id = Column(String, ForeignKey("knockout_brackets.id", ondelete="SET NULL"), nullable=True, index=True)
    round = Column(Integer, nullable=True)
    match_number = Column(Integer, nullable=True)
    scheduled_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    team_a_id = Column(String, nullable=True, index=True)
    team_b_id = Column(String, nullable=True, index=True)
    format = Column(String, nullable=False, default="BO1")
    status = Column(String, nullable=False, default="SCHEDULED", index=True)
    score_a = Column(Integer, nullable=True)
    score_b = Column(Integer, nullable=True)
    kills_a = Column(Integer, nullable=True)
    kills_b = Column(Integer, nullable=True)
    deaths_a = Column(Integer, nullable=True)
    deaths_b = Column(Integer, nullable=True)
    winner_team_id = Column(String, nullable=True, index=True)
    result_image_path = Column(String, nullable=True)
    result_confidence = Column(Float, nullable=True)
    ocr_raw_result_json = Column(Text, nullable=True)
    result_metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tournament = relationship("Tournament", back_populates="matches")
    group = relationship("TournamentGroup", back_populates="matches")
    bracket = relationship("KnockoutBracket", back_populates="matches")
    result_versions = relationship("MatchResultVersion", back_populates="match", cascade="all, delete-orphan")
    map_results = relationship("BracketMatchMap", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_matches_tournament_stage", "tournament_id", "stage"),
        Index("ix_matches_scheduled_date", "scheduled_date"),
    )


class BracketMatchMap(Base):
    __tablename__ = "bracket_match_maps"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    match_id = Column(String, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    map_number = Column(Integer, nullable=False)
    team_a_id = Column(String, nullable=True)
    team_b_id = Column(String, nullable=True)
    winner_team_id = Column(String, nullable=True)
    score_a = Column(Integer, nullable=True)
    score_b = Column(Integer, nullable=True)
    kills_a = Column(Integer, nullable=True)
    kills_b = Column(Integer, nullable=True)
    deaths_a = Column(Integer, nullable=True)
    deaths_b = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="PENDING", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="map_results")

    __table_args__ = (
        UniqueConstraint("match_id", "map_number", name="uq_match_map_number"),
    )


class MatchResultVersion(Base):
    __tablename__ = "match_result_versions"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    match_id = Column(String, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    score_a = Column(Integer, nullable=True)
    score_b = Column(Integer, nullable=True)
    kills_a = Column(Integer, nullable=True)
    kills_b = Column(Integer, nullable=True)
    deaths_a = Column(Integer, nullable=True)
    deaths_b = Column(Integer, nullable=True)
    winner_team_id = Column(String, nullable=True)
    ocr_raw_json = Column(Text, nullable=True)
    changed_by = Column(String, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
    change_reason = Column(String, nullable=True)
    verified = Column(Boolean, nullable=False, default=False)

    match = relationship("Match", back_populates="result_versions")

    __table_args__ = (
        UniqueConstraint("match_id", "version", name="uq_match_result_version"),
    )


class GroupStanding(Base):
    __tablename__ = "group_standings"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    group_id = Column(String, ForeignKey("tournament_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String, nullable=False, index=True)
    rank = Column(Integer, nullable=True)
    played = Column(Integer, nullable=False, default=0)
    win = Column(Integer, nullable=False, default=0)
    loss = Column(Integer, nullable=False, default=0)
    kill = Column(Integer, nullable=False, default=0)
    death = Column(Integer, nullable=False, default=0)
    kill_difference = Column(Integer, nullable=False, default=0)
    points = Column(Integer, nullable=False, default=0)
    computed_at = Column(DateTime, default=datetime.utcnow)
    is_manual_override = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("group_id", "team_id", name="uq_group_team_standing"),
        Index("ix_group_standings_group_points", "group_id", "points", "kill_difference", "kill"),
    )


class KnockoutBracket(Base):
    __tablename__ = "knockout_brackets"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    bracket_type = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=True)

    tournament = relationship("Tournament", back_populates="brackets")
    rounds = relationship("KnockoutRound", back_populates="bracket", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="bracket")

    __table_args__ = (
        UniqueConstraint("tournament_id", "name", name="uq_tournament_bracket_name"),
    )


class KnockoutRound(Base):
    __tablename__ = "knockout_rounds"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    bracket_id = Column(String, ForeignKey("knockout_brackets.id", ondelete="CASCADE"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    round_name = Column(String, nullable=True)

    bracket = relationship("KnockoutBracket", back_populates="rounds")
    slots = relationship("KnockoutSlot", back_populates="round", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("bracket_id", "round_number", name="uq_bracket_round"),
    )


class KnockoutSlot(Base):
    __tablename__ = "knockout_slots"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    round_id = Column(String, ForeignKey("knockout_rounds.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_number = Column(Integer, nullable=False)
    team_id = Column(String, nullable=True, index=True)
    next_match_id = Column(String, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)
    next_slot_number = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="EMPTY", index=True)

    round = relationship("KnockoutRound", back_populates="slots")

    __table_args__ = (
        UniqueConstraint("round_id", "slot_number", name="uq_round_slot"),
    )


class ScheduleVersion(Base):
    __tablename__ = "schedule_versions"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)

    tournament = relationship("Tournament", back_populates="schedule_versions")

    __table_args__ = (
        UniqueConstraint("tournament_id", "version", name="uq_tournament_schedule_version"),
    )


class TournamentPlacement(Base):
    __tablename__ = "tournament_placements"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String, nullable=False, index=True)
    placement = Column(Integer, nullable=False)
    source = Column(String, nullable=True)

    tournament = relationship("Tournament", back_populates="placements")

    __table_args__ = (
        UniqueConstraint("tournament_id", "team_id", name="uq_tournament_team_placement"),
        UniqueConstraint("tournament_id", "placement", name="uq_tournament_placement"),
    )


class BracketQualification(Base):
    __tablename__ = "bracket_qualifications"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String, ForeignKey("tournament_groups.id", ondelete="CASCADE"), nullable=True, index=True)
    team_id = Column(String, nullable=False, index=True)
    bracket_type = Column(String, nullable=False, index=True)
    rank = Column(Integer, nullable=True)

    tournament = relationship("Tournament", back_populates="bracket_qualifications")
    group = relationship("TournamentGroup")

    __table_args__ = (
        UniqueConstraint("tournament_id", "team_id", name="uq_bracket_team"),
        Index("ix_bracket_qualifications_tournament_bracket", "tournament_id", "bracket_type"),
    )


class BracketMatch(Base):
    __tablename__ = "bracket_matches"

    id = Column(String, primary_key=True, default=uuid_str, index=True)
    tournament_id = Column(String, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    bracket_id = Column(String, ForeignKey("knockout_brackets.id", ondelete="CASCADE"), nullable=False, index=True)
    round_id = Column(String, ForeignKey("knockout_rounds.id", ondelete="CASCADE"), nullable=True, index=True)
    slot_number = Column(Integer, nullable=False)
    team_a_id = Column(String, nullable=True, index=True)
    team_b_id = Column(String, nullable=True, index=True)
    winner_team_id = Column(String, nullable=True, index=True)
    loser_next_match_id = Column(String, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)
    loser_next_slot = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="SCHEDULED", index=True)
    scheduled_date = Column(Date, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    format = Column(String, nullable=False, default="BO1")
    score_a = Column(Integer, nullable=True)
    score_b = Column(Integer, nullable=True)
    kills_a = Column(Integer, nullable=True)
    kills_b = Column(Integer, nullable=True)
    deaths_a = Column(Integer, nullable=True)
    deaths_b = Column(Integer, nullable=True)

    bracket = relationship("KnockoutBracket")
    round = relationship("KnockoutRound")

    __table_args__ = (
        UniqueConstraint("bracket_id", "round_id", "slot_number", name="uq_bracket_match_slot"),
    )
