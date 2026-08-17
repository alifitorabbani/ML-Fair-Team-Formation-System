from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
import json

from app.database import get_db
from app.tournament.services.tournament_service import TournamentService
from app.tournament.services.schedule_service import ScheduleService
from app.tournament.services.match_service import MatchService
from app.tournament.services.group_service import GroupService
from app.tournament.services.standings_service import StandingsService
from app.tournament.services.bracket_service import BracketService
from app.tournament.services.placement_service import PlacementService
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
    BracketQualificationCreate,
    ScheduleConfig,
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


@router.get("/{tournament_id}/teams")
async def list_tournament_teams(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    teams = await service.team_repo.get_by_tournament(tournament_id)
    return [
        {
            "id": t.id,
            "tournament_id": t.tournament_id,
            "team_version_id": t.team_version_id,
            "team_id": t.team_id,
            "team_name_snapshot": t.team_name_snapshot,
            "seed": t.seed,
        }
        for t in teams
    ]


@router.get("/{tournament_id}/available-teams")
async def list_available_teams(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    all_teams = await service.team_repo.get_by_tournament(tournament_id)
    groups = await service.group_repo.get_by_tournament(tournament_id)
    assigned_team_ids = set()
    for group in groups:
        members = await service.group_member_repo.get_by_group(group.id)
        for m in members:
            if m.tournament_team and m.tournament_team.team_id:
                assigned_team_ids.add(m.tournament_team.team_id)
    available = [
        {
            "id": t.id,
            "tournament_id": t.tournament_id,
            "team_version_id": t.team_version_id,
            "team_id": t.team_id,
            "team_name_snapshot": t.team_name_snapshot,
            "seed": t.seed,
        }
        for t in all_teams
        if t.team_id not in assigned_team_ids
    ]
    if not available:
        tournament = await service.tournament_repo.get_by_id(tournament_id)
        if tournament and tournament.selected_team_version_id:
            from app.repositories.team_repository import TeamRepository
            team_repo = TeamRepository(db)
            version_members = await team_repo.get_members_by_version(tournament.selected_team_version_id)
            seen = set()
            for m in version_members:
                if not m.team_id or m.team_id in seen:
                    continue
                seen.add(m.team_id)
                available.append({
                    "id": None,
                    "tournament_id": tournament_id,
                    "team_version_id": tournament.selected_team_version_id,
                    "team_id": m.team_id,
                    "team_name_snapshot": None,
                    "seed": None,
                })
    return available


@router.post("/{tournament_id}/groups/auto-assign")
async def auto_assign_groups(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    try:
        from app.tournament.services.group_service import GroupService
        from app.repositories.team_repository import TeamRepository
        from app.repositories.participant_repository import ParticipantRepository

        group_service = GroupService(db)
        team_repo = TeamRepository(db)
        participant_repo = ParticipantRepository(db)

        tournament = await group_service.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise HTTPException(status_code=404, detail="Tournament not found")

        tournament_teams = await group_service.team_repo.get_by_tournament(tournament_id)
        if not tournament_teams:
            version_id = tournament.selected_team_version_id
            if not version_id:
                latest_version = await team_repo.get_active()
                if not latest_version:
                    raise HTTPException(status_code=400, detail="No teams in tournament. Generate or select a team version first.")
                version_id = latest_version.id
            version_members = await team_repo.get_members_by_version(version_id)
            team_ids = sorted({m.team_id for m in version_members if m.team_id})
            for idx, team_id in enumerate(team_ids):
                await group_service.team_repo.create(
                    {
                        "tournament_id": tournament_id,
                        "team_version_id": version_id,
                        "team_id": team_id,
                        "seed": idx + 1,
                    }
                )
            tournament_teams = await group_service.team_repo.get_by_tournament(tournament_id)
            if not tournament_teams:
                raise HTTPException(status_code=400, detail="No teams available from selected team version.")

        groups = await group_service.group_repo.get_by_tournament(tournament_id)
        if not groups:
            raise HTTPException(status_code=400, detail="No groups created. Create groups first.")

        team_skills = []
        for tt in tournament_teams:
            try:
                members = await team_repo.get_members_by_version(tt.team_version_id)
                player_ids = [m.player_id for m in members if m.player_id]
                if not player_ids:
                    team_skills.append({
                        "team_id": tt.team_id,
                        "tournament_team_id": tt.id,
                        "skill_score": 0.0,
                    })
                    continue
                participants = await participant_repo.get_by_ids(player_ids)
                participants_map = {p.id: p for p in participants}
                total_skill = 0.0
                count = 0
                for m in members:
                    p = participants_map.get(m.player_id)
                    if p and p.skill_score is not None:
                        total_skill += p.skill_score
                        count += 1
                avg_skill = total_skill / count if count > 0 else 0.0
                team_skills.append({
                    "team_id": tt.team_id,
                    "tournament_team_id": tt.id,
                    "skill_score": avg_skill,
                })
            except Exception:
                team_skills.append({
                    "team_id": tt.team_id,
                    "tournament_team_id": tt.id,
                    "skill_score": 0.0,
                })

        if not team_skills:
            raise HTTPException(status_code=400, detail="No valid team data")

        team_skills.sort(key=lambda x: x["skill_score"], reverse=True)

        group_count = len(groups)
        assignments: Dict[str, List[str]] = {g.id: [] for g in groups}

        for i, team in enumerate(team_skills):
            if group_count == 1:
                assignments[groups[0].id].append(team["tournament_team_id"])
            else:
                round_num = i // group_count
                pos_in_round = i % group_count
                is_reverse = round_num % 2 == 1
                group_idx = (group_count - 1 - pos_in_round) if is_reverse else pos_in_round
                assignments[groups[group_idx].id].append(team["tournament_team_id"])

        result = []
        for group in groups:
            await group_service.group_member_repo.delete_by_group(group.id)
            for seed_idx, tournament_team_id in enumerate(assignments[group.id], 1):
                await group_service.group_member_repo.create(
                    {
                        "group_id": group.id,
                        "tournament_team_id": tournament_team_id,
                        "seed": seed_idx,
                    }
                )
            members = await group_service.group_member_repo.get_by_group(group.id)
            result.append({
                "id": group.id,
                "name": group.name,
                "assigned_count": len(members),
            })

        return {"groups": result}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Auto-assign failed: {type(e).__name__}: {e}")


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


@router.post("/{tournament_id}/groups/clear")
async def clear_groups(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = TournamentService(db)
    try:
        await service.clear_groups(tournament_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "All groups cleared"}


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
async def generate_schedule(tournament_id: str, config: Optional[ScheduleConfig] = None, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    service = ScheduleService(db)
    try:
        result = await service.generate_schedule(
            tournament_id,
            created_by="admin",
            start_date=config.start_date if config else None,
            end_date=config.end_date if config else None,
            match_duration_minutes=config.match_duration_minutes if config else None,
            bo_format=config.bo_format if config else None,
            min_rest_minutes=config.min_rest_minutes if config else None,
            buffer_minutes=config.buffer_minutes if config else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Schedule generation failed: {type(e).__name__}: {e}")
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
        map_results = None
        if hasattr(data, 'map_results') and data.map_results:
            map_results = [m.model_dump() for m in data.map_results]
        match = await service.submit_match_result(
            tournament_id,
            match_id,
            data,
            map_results=map_results,
        )
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


@router.post("/{tournament_id}/bracket-qualifications")
async def set_bracket_qualification(tournament_id: str, data: BracketQualificationCreate, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    from app.tournament.repositories.bracket_qualification_repository import BracketQualificationRepository
    repo = BracketQualificationRepository(db)
    existing = await repo.get_by_team(tournament_id, data.team_id)
    if existing:
        existing.bracket_type = data.bracket_type
        existing.group_id = data.group_id
        existing.rank = data.rank
        await db.flush()
        await db.refresh(existing)
        return {"id": existing.id, "tournament_id": existing.tournament_id, "team_id": existing.team_id, "bracket_type": existing.bracket_type, "group_id": existing.group_id, "rank": existing.rank}
    qualification = await repo.create({
        "tournament_id": tournament_id,
        "group_id": data.group_id,
        "team_id": data.team_id,
        "bracket_type": data.bracket_type,
        "rank": data.rank,
    })
    return {"id": qualification.id, "tournament_id": qualification.tournament_id, "team_id": qualification.team_id, "bracket_type": qualification.bracket_type, "group_id": qualification.group_id, "rank": qualification.rank}


@router.get("/{tournament_id}/bracket-qualifications")
async def get_bracket_qualifications(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    from app.tournament.repositories.bracket_qualification_repository import BracketQualificationRepository
    repo = BracketQualificationRepository(db)
    qualifications = await repo.get_by_tournament(tournament_id)
    return [
        {
            "id": q.id,
            "tournament_id": q.tournament_id,
            "group_id": q.group_id,
            "team_id": q.team_id,
            "bracket_type": q.bracket_type,
            "rank": q.rank,
        }
        for q in qualifications
    ]


@router.delete("/{tournament_id}/bracket-qualifications")
async def clear_bracket_qualifications(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    from app.tournament.repositories.bracket_qualification_repository import BracketQualificationRepository
    repo = BracketQualificationRepository(db)
    await repo.delete_by_tournament(tournament_id)
    return {"message": "Bracket qualifications cleared"}


@router.post("/{tournament_id}/knockout/generate")
async def generate_knockout(tournament_id: str, data: Dict[str, Any] = None, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    if not data:
        raise HTTPException(status_code=400, detail="Request body is required")
    qualified_team_ids = data.get("qualified_team_ids", [])
    populate_matches = data.get("populate_matches", True)
    if len(qualified_team_ids) != 8:
        raise HTTPException(status_code=400, detail=f"Exactly 8 qualified teams required, got {len(qualified_team_ids)}")
    bracket_service = BracketService(db)
    try:
        result = await bracket_service.generate_bracket(
            tournament_id,
            qualified_team_ids,
            populate_matches=populate_matches,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "message": "Bracket generated successfully",
        "upper_bracket_id": result["upper_bracket"].id,
        "lower_bracket_id": result["lower_bracket"].id,
    }


@router.get("/{tournament_id}/knockout")
async def get_knockout(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    bracket_service = BracketService(db)
    bracket_data = await bracket_service.get_bracket(tournament_id)
    return bracket_data


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


@router.post("/{tournament_id}/knockout/reset")
async def reset_bracket(tournament_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _ = get_admin_user(x_user_token)
    bracket_service = BracketService(db)
    try:
        result = await bracket_service.reset_bracket(tournament_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Bracket reset successfully"}


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
