from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json

from app.database import get_db
from app.tournament.services.tournament_service import TournamentService
from app.tournament.services.schedule_service import ScheduleService
from app.tournament.services.match_service import MatchService
from app.tournament.services.group_service import GroupService
from app.tournament.services.standings_service import StandingsService
from app.tournament.services.bracket_service import BracketService
from app.tournament.services.placement_service import PlacementService
from app.tournament.services.ocr_service import OCRService
from app.tournament.schemas.tournament_schemas import (
    TournamentCreate,
    TournamentUpdate,
    TournamentTeamSelect,
    TournamentGroupCreate,
    TournamentGroupUpdate,
    MatchCreate,
    MatchUpdate,
    MatchResultSubmit,
    StandingsOverride,
    PlacementSet,
    MatchResultOCRResponse,
    TournamentResponse,
    TournamentDateResponse,
    TournamentTeamResponse,
    GroupResponse,
    GroupMemberResponse,
    MatchResponse,
    StandingResponse,
    BracketResponse,
    BracketSlotResponse,
    PlacementResponse,
    ScheduleGenerateResponse,
)
from app.tournament.constants import TournamentStatus, MatchStage, MatchStatus, BOFormat, BracketType, ThirdPlaceMode
from app.api.deps import get_admin_user

router = APIRouter(prefix="/api/admin/tournaments", tags=["admin-tournaments"])


def _tournament_to_response(tournament) -> TournamentResponse:
    return TournamentResponse(
        id=tournament.id,
        name=tournament.name,
        description=tournament.description,
        timezone=tournament.timezone,
        status=tournament.status,
        third_place_mode=tournament.third_place_mode,
        selected_team_version_id=tournament.selected_team_version_id,
        champion_team_id=tournament.champion_team_id,
        runner_up_team_id=tournament.runner_up_team_id,
        third_place_team_id=tournament.third_place_team_id,
        created_by=tournament.created_by,
        created_at=tournament.created_at,
        updated_at=tournament.updated_at,
        finalized_at=tournament.finalized_at,
    )


@router.post("", response_model=TournamentResponse)
async def create_tournament(data: TournamentCreate, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    tournament = await service.create_tournament(data, created_by="admin")
    return _tournament_to_response(tournament)


@router.get("", response_model=List[TournamentResponse])
async def list_tournaments(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    tournaments = await service.list_tournaments()
    return [_tournament_to_response(t) for t in tournaments]


@router.get("/{tournament_id}", response_model=TournamentResponse)
async def get_tournament(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    result = await service.get_tournament(tournament_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return _tournament_to_response(result["tournament"])


@router.patch("/{tournament_id}", response_model=TournamentResponse)
async def update_tournament(tournament_id: str, data: TournamentUpdate, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    tournament = await service.update_tournament(tournament_id, data)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return _tournament_to_response(tournament)


@router.delete("/{tournament_id}")
async def delete_tournament(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    success = await service.delete_tournament(tournament_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return {"message": "Tournament deleted"}


@router.post("/{tournament_id}/teams", response_model=TournamentTeamResponse)
async def select_teams(tournament_id: str, data: TournamentTeamSelect, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        tournament = await service.select_teams(tournament_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    teams = await service.team_repo.get_by_tournament(tournament_id)
    return TournamentTeamResponse(
        id=teams[0].id if teams else "",
        tournament_id=tournament_id,
        team_version_id=data.team_version_id,
        team_id=teams[0].team_id if teams else "",
        team_name_snapshot=teams[0].team_name_snapshot if teams else None,
        seed=teams[0].seed if teams else None,
    )


@router.get("/{tournament_id}/groups")
async def list_groups(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    group_service = GroupService(db)
    groups = await group_service.list_groups(tournament_id)
    result = []
    for group in groups:
        members = await group_service.group_member_repo.get_by_group(group.id)
        result.append({
            "id": group.id,
            "tournament_id": group.tournament_id,
            "name": group.name,
            "sort_order": group.sort_order,
            "members": [
                {
                    "id": m.id,
                    "group_id": m.group_id,
                    "tournament_team_id": m.tournament_team_id,
                    "seed": m.seed,
                    "team_id": m.tournament_team.team_id if m.tournament_team else None,
                    "team_name_snapshot": m.tournament_team.team_name_snapshot if m.tournament_team else None,
                }
                for m in members
            ],
        })
    return result


@router.post("/{tournament_id}/groups", response_model=GroupResponse)
async def create_group(tournament_id: str, data: TournamentGroupCreate, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        group = await service.create_groups(tournament_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return GroupResponse(id=group.id, tournament_id=group.tournament_id, name=group.name, sort_order=group.sort_order)


@router.patch("/{tournament_id}/groups/{group_id}", response_model=GroupResponse)
async def update_group(tournament_id: str, group_id: str, data: TournamentGroupUpdate, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        group = await service.update_group(group_id, data.name, data.team_ids, data.sort_order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupResponse(id=group.id, tournament_id=group.tournament_id, name=group.name, sort_order=group.sort_order)


@router.post("/{tournament_id}/groups/finalize", response_model=TournamentResponse)
async def finalize_group_stage(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        tournament = await service.finalize_group_stage(tournament_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _tournament_to_response(tournament)


@router.post("/{tournament_id}/groups/reopen", response_model=TournamentResponse)
async def reopen_group_stage(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        tournament = await service.reopen_group_stage(tournament_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _tournament_to_response(tournament)


@router.post("/{tournament_id}/schedule/generate", response_model=ScheduleGenerateResponse)
async def generate_schedule(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = ScheduleService(db)
    try:
        result = await service.generate_schedule(tournament_id, created_by="admin")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/{tournament_id}/schedule")
async def get_schedule(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
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
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in matches
    ]


@router.get("/{tournament_id}/schedule/versions")
async def get_schedule_versions(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = ScheduleService(db)
    versions = await service.get_schedule_versions(tournament_id)
    return [
        {
            "id": v.id,
            "tournament_id": v.tournament_id,
            "version": v.version,
            "created_by": v.created_by,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "notes": v.notes,
        }
        for v in versions
    ]


@router.post("/{tournament_id}/matches", response_model=MatchResponse)
async def create_match(tournament_id: str, data: MatchCreate, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        match = await service.create_match(tournament_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MatchResponse(
        id=match.id,
        tournament_id=match.tournament_id,
        stage=match.stage,
        group_id=match.group_id,
        bracket_id=match.bracket_id,
        round=match.round,
        match_number=match.match_number,
        scheduled_date=match.scheduled_date,
        start_time=match.start_time,
        end_time=match.end_time,
        team_a_id=match.team_a_id,
        team_b_id=match.team_b_id,
        format=match.format,
        status=match.status,
        score_a=match.score_a,
        score_b=match.score_b,
        kills_a=match.kills_a,
        kills_b=match.kills_b,
        deaths_a=match.deaths_a,
        deaths_b=match.deaths_b,
        winner_team_id=match.winner_team_id,
        result_confidence=match.result_confidence,
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


@router.patch("/{tournament_id}/matches/{match_id}", response_model=MatchResponse)
async def update_match(tournament_id: str, match_id: str, data: MatchUpdate, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        match = await service.update_match(tournament_id, match_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return MatchResponse(
        id=match.id,
        tournament_id=match.tournament_id,
        stage=match.stage,
        group_id=match.group_id,
        bracket_id=match.bracket_id,
        round=match.round,
        match_number=match.match_number,
        scheduled_date=match.scheduled_date,
        start_time=match.start_time,
        end_time=match.end_time,
        team_a_id=match.team_a_id,
        team_b_id=match.team_b_id,
        format=match.format,
        status=match.status,
        score_a=match.score_a,
        score_b=match.score_b,
        kills_a=match.kills_a,
        kills_b=match.kills_b,
        deaths_a=match.deaths_a,
        deaths_b=match.deaths_b,
        winner_team_id=match.winner_team_id,
        result_confidence=match.result_confidence,
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


@router.delete("/{tournament_id}/matches/{match_id}")
async def delete_match(tournament_id: str, match_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        success = await service.delete_match(tournament_id, match_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not success:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"message": "Match deleted"}


@router.post("/{tournament_id}/matches/{match_id}/result", response_model=MatchResponse)
async def submit_result(tournament_id: str, match_id: str, data: MatchResultSubmit, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        match = await service.submit_match_result(tournament_id, match_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MatchResponse(
        id=match.id,
        tournament_id=match.tournament_id,
        stage=match.stage,
        group_id=match.group_id,
        bracket_id=match.bracket_id,
        round=match.round,
        match_number=match.match_number,
        scheduled_date=match.scheduled_date,
        start_time=match.start_time,
        end_time=match.end_time,
        team_a_id=match.team_a_id,
        team_b_id=match.team_b_id,
        format=match.format,
        status=match.status,
        score_a=match.score_a,
        score_b=match.score_b,
        kills_a=match.kills_a,
        kills_b=match.kills_b,
        deaths_a=match.deaths_a,
        deaths_b=match.deaths_b,
        winner_team_id=match.winner_team_id,
        result_confidence=match.result_confidence,
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


@router.post("/{tournament_id}/matches/{match_id}/result/confirm", response_model=MatchResponse)
async def confirm_result(tournament_id: str, match_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        match = await service.confirm_match_result(tournament_id, match_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return MatchResponse(
        id=match.id,
        tournament_id=match.tournament_id,
        stage=match.stage,
        group_id=match.group_id,
        bracket_id=match.bracket_id,
        round=match.round,
        match_number=match.match_number,
        scheduled_date=match.scheduled_date,
        start_time=match.start_time,
        end_time=match.end_time,
        team_a_id=match.team_a_id,
        team_b_id=match.team_b_id,
        format=match.format,
        status=match.status,
        score_a=match.score_a,
        score_b=match.score_b,
        kills_a=match.kills_a,
        kills_b=match.kills_b,
        deaths_a=match.deaths_a,
        deaths_b=match.deaths_b,
        winner_team_id=match.winner_team_id,
        result_confidence=match.result_confidence,
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


@router.post("/{tournament_id}/matches/{match_id}/result/ocr", response_model=MatchResultOCRResponse)
async def upload_result_ocr(tournament_id: str, match_id: str, file: UploadFile = File(...), x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    match = await MatchService(db).match_repo.get_by_id(match_id)
    if not match or match.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Match not found")
    contents = await file.read()
    ocr_service = OCRService()
    result = ocr_service.extract_result(contents, match.format, team_a_id=match.team_a_id, team_b_id=match.team_b_id)
    validated = ocr_service.validate_against_match(result, match.team_a_id, match.team_b_id)
    return MatchResultOCRResponse(
        match_id=match_id,
        team_a_name=validated.get("team_a_name"),
        team_b_name=validated.get("team_b_name"),
        score_a=validated.get("score_a"),
        score_b=validated.get("score_b"),
        kills_a=validated.get("kills_a"),
        kills_b=validated.get("kills_b"),
        deaths_a=validated.get("deaths_a"),
        deaths_b=validated.get("deaths_b"),
        winner_team_id=validated.get("winner_team_id"),
        confidence=validated.get("confidence", 0.0),
        is_valid=validated.get("is_valid", False),
        validation_message=validated.get("validation_message"),
        raw_text=validated.get("raw_text"),
    )


@router.get("/{tournament_id}/standings")
async def get_group_standings(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
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


@router.patch("/{tournament_id}/standings/override")
async def override_standings(tournament_id: str, data: List[StandingsOverride], x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    if not data:
        raise HTTPException(status_code=400, detail="No overrides provided")
    group_id = data[0].group_id if hasattr(data[0], "group_id") else None
    if not group_id:
        raise HTTPException(status_code=400, detail="group_id required in override data")
    service = TournamentService(db)
    results = await service.override_standings(tournament_id, group_id, data, actor="admin")
    return [
        {
            "id": r.id,
            "group_id": r.group_id,
            "team_id": r.team_id,
            "rank": r.rank,
            "played": r.played,
            "win": r.win,
            "loss": r.loss,
            "kill": r.kill,
            "death": r.death,
            "kill_difference": r.kill_difference,
            "points": r.points,
            "is_manual_override": r.is_manual_override,
        }
        for r in results
    ]


@router.post("/{tournament_id}/standings/recalculate")
async def recalculate_standings(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    group_service = GroupService(db)
    groups = await group_service.list_groups(tournament_id)
    results = []
    for group in groups:
        standings = await group_service.recalculate_group_standings(tournament_id, group.id)
        results.append(
            {
                "group_id": group.id,
                "group_name": group.name,
                "standings": standings,
            }
        )
    return results


@router.post("/{tournament_id}/knockout/generate")
async def generate_knockout(tournament_id: str, bracket_type: str = "UPPER", qualified_team_ids: Optional[List[str]] = None, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    if not qualified_team_ids:
        raise HTTPException(status_code=400, detail="qualified_team_ids required")
    bracket_service = BracketService(db)
    try:
        bracket = await bracket_service.generate_bracket(tournament_id, bracket_type, qualified_team_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": bracket.id,
        "tournament_id": bracket.tournament_id,
        "name": bracket.name,
        "bracket_type": bracket.bracket_type,
        "sort_order": bracket.sort_order,
    }


@router.get("/{tournament_id}/knockout")
async def get_knockout(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    bracket_service = BracketService(db)
    brackets = await bracket_service.get_bracket(tournament_id)
    return brackets


@router.post("/{tournament_id}/knockout/{match_id}/advance")
async def advance_knockout(tournament_id: str, match_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    bracket_service = BracketService(db)
    try:
        match = await bracket_service.advance_winner(tournament_id, match_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"message": "Winner advanced", "match_id": match.id, "winner_team_id": match.winner_team_id}


@router.post("/{tournament_id}/placements/{team_id}", response_model=PlacementResponse)
async def set_placement(tournament_id: str, team_id: str, placement: int, source: Optional[str] = None, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    placement_service = PlacementService(db)
    try:
        p = await placement_service.set_placement(tournament_id, team_id, placement, source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PlacementResponse(id=p.id, tournament_id=p.tournament_id, team_id=p.team_id, placement=p.placement, source=p.source)


@router.post("/{tournament_id}/champion/finalize", response_model=TournamentResponse)
async def finalize_champion(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    placement_service = PlacementService(db)
    try:
        tournament = await placement_service.finalize_placements(tournament_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _tournament_to_response(tournament)


@router.post("/{tournament_id}/finalize", response_model=TournamentResponse)
async def finalize_tournament(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    placement_service = PlacementService(db)
    try:
        tournament = await placement_service.finalize_placements(tournament_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _tournament_to_response(tournament)
