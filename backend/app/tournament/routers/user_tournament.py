from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.tournament.services.tournament_service import TournamentService
from app.tournament.services.schedule_service import ScheduleService
from app.tournament.services.group_service import GroupService
from app.tournament.services.bracket_service import BracketService
from app.tournament.services.placement_service import PlacementService
from app.tournament.constants import TournamentStatus

router = APIRouter(prefix="/api/tournaments", tags=["user-tournaments"])


@router.get("")
async def list_tournaments(db: AsyncSession = Depends(get_db)):
    service = TournamentService(db)
    tournaments = await service.list_tournaments()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "status": t.status,
            "timezone": t.timezone,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tournaments
    ]


@router.get("/{tournament_id}")
async def get_tournament(tournament_id: str, db: AsyncSession = Depends(get_db)):
    service = TournamentService(db)
    result = await service.get_tournament(tournament_id)
    if not result:
        return {"error": "Tournament not found"}
    tournament = result["tournament"]
    return {
        "id": tournament.id,
        "name": tournament.name,
        "description": tournament.description,
        "status": tournament.status,
        "timezone": tournament.timezone,
        "third_place_mode": tournament.third_place_mode,
        "champion_team_id": tournament.champion_team_id,
        "runner_up_team_id": tournament.runner_up_team_id,
        "third_place_team_id": tournament.third_place_team_id,
        "created_at": tournament.created_at.isoformat() if tournament.created_at else None,
        "updated_at": tournament.updated_at.isoformat() if tournament.updated_at else None,
        "finalized_at": tournament.finalized_at.isoformat() if tournament.finalized_at else None,
        "dates": [
            {
                "id": d.id,
                "date": d.date.isoformat() if d.date else None,
                "start_time": d.start_time.isoformat() if d.start_time else None,
                "end_time": d.end_time.isoformat() if d.end_time else None,
                "match_duration_minutes": d.match_duration_minutes,
                "buffer_minutes": d.buffer_minutes,
                "min_rest_minutes": d.min_rest_minutes,
            }
            for d in result["dates"]
        ],
        "teams": [
            {
                "id": t.id,
                "team_version_id": t.team_version_id,
                "team_id": t.team_id,
                "team_name_snapshot": t.team_name_snapshot,
                "seed": t.seed,
            }
            for t in result["teams"]
        ],
    }


@router.get("/{tournament_id}/schedule")
async def get_schedule(tournament_id: str, db: AsyncSession = Depends(get_db)):
    service = ScheduleService(db)
    matches = await service.get_schedule(tournament_id)
    return [
        {
            "id": m.id,
            "stage": m.stage,
            "group_id": m.group_id,
            "bracket_id": m.bracket_id,
            "round": m.round,
            "match_number": m.match_number,
            "scheduled_date": m.scheduled_date.isoformat() if m.scheduled_date else None,
            "start_time": m.start_time.isoformat() if m.start_time else None,
            "end_time": m.end_time.isoformat() if m.end_time else None,
            "team_a_id": m.team_a_id,
            "team_b_id": m.team_b_id,
            "format": m.format,
            "status": m.status,
            "score_a": m.score_a,
            "score_b": m.score_b,
            "kills_a": m.kills_a,
            "kills_b": m.kills_b,
            "deaths_a": m.deaths_a,
            "deaths_b": m.deaths_b,
            "winner_team_id": m.winner_team_id,
            "result_confidence": m.result_confidence,
        }
        for m in matches
    ]


@router.get("/{tournament_id}/matches")
async def get_matches(tournament_id: str, db: AsyncSession = Depends(get_db)):
    service = TournamentService(db)
    matches = await service.match_repo.get_by_tournament(tournament_id)
    return [
        {
            "id": m.id,
            "stage": m.stage,
            "group_id": m.group_id,
            "bracket_id": m.bracket_id,
            "round": m.round,
            "match_number": m.match_number,
            "scheduled_date": m.scheduled_date.isoformat() if m.scheduled_date else None,
            "start_time": m.start_time.isoformat() if m.start_time else None,
            "end_time": m.end_time.isoformat() if m.end_time else None,
            "team_a_id": m.team_a_id,
            "team_b_id": m.team_b_id,
            "format": m.format,
            "status": m.status,
            "score_a": m.score_a,
            "score_b": m.score_b,
            "kills_a": m.kills_a,
            "kills_b": m.kills_b,
            "deaths_a": m.deaths_a,
            "deaths_b": m.deaths_b,
            "winner_team_id": m.winner_team_id,
            "result_confidence": m.result_confidence,
        }
        for m in matches
    ]


@router.get("/{tournament_id}/standings")
async def get_standings(tournament_id: str, db: AsyncSession = Depends(get_db)):
    group_service = GroupService(db)
    groups = await group_service.list_groups(tournament_id)
    results = []
    for group in groups:
        standings = await group_service.get_group_standings(group.id)
        results.append(
            {
                "group_id": group.id,
                "group_name": group.name,
                "standings": standings,
            }
        )
    return results


@router.get("/{tournament_id}/knockout")
async def get_knockout(tournament_id: str, db: AsyncSession = Depends(get_db)):
    bracket_service = BracketService(db)
    brackets = await bracket_service.get_bracket(tournament_id)
    return brackets


@router.get("/{tournament_id}/results")
async def get_results(tournament_id: str, db: AsyncSession = Depends(get_db)):
    service = TournamentService(db)
    matches = await service.match_repo.get_by_tournament(tournament_id)
    return [
        {
            "id": m.id,
            "stage": m.stage,
            "group_id": m.group_id,
            "bracket_id": m.bracket_id,
            "round": m.round,
            "match_number": m.match_number,
            "scheduled_date": m.scheduled_date.isoformat() if m.scheduled_date else None,
            "team_a_id": m.team_a_id,
            "team_b_id": m.team_b_id,
            "format": m.format,
            "status": m.status,
            "score_a": m.score_a,
            "score_b": m.score_b,
            "kills_a": m.kills_a,
            "kills_b": m.kills_b,
            "deaths_a": m.deaths_a,
            "deaths_b": m.deaths_b,
            "winner_team_id": m.winner_team_id,
            "result_confidence": m.result_confidence,
        }
        for m in matches
        if m.status == "COMPLETED"
    ]


@router.get("/{tournament_id}/placements")
async def get_placements(tournament_id: str, db: AsyncSession = Depends(get_db)):
    placement_service = PlacementService(db)
    placements = await placement_service.get_placements(tournament_id)
    return [
        {
            "id": p.id,
            "team_id": p.team_id,
            "placement": p.placement,
            "source": p.source,
        }
        for p in placements
    ]
