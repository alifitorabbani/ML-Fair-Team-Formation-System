from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import Tournament, TournamentPlacement
from app.tournament.repositories import TournamentRepository, TournamentPlacementRepository
from app.tournament.constants import TournamentStatus


class PlacementService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tournament_repo = TournamentRepository(db)
        self.placement_repo = TournamentPlacementRepository(db)

    async def set_placement(self, tournament_id: str, team_id: str, placement: int, source: Optional[str] = None) -> TournamentPlacement:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        existing = await self.placement_repo.get_by_tournament_and_team(tournament_id, team_id)
        if existing:
            existing.placement = placement
            if source is not None:
                existing.source = source
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        return await self.placement_repo.create(
            {
                "tournament_id": tournament_id,
                "team_id": team_id,
                "placement": placement,
                "source": source,
            }
        )

    async def get_placements(self, tournament_id: str) -> List[TournamentPlacement]:
        return await self.placement_repo.get_by_tournament(tournament_id)

    async def finalize_placements(self, tournament_id: str) -> Tournament:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        placements = await self.placement_repo.get_by_tournament(tournament_id)
        for placement in placements:
            if placement.placement == 1:
                tournament.champion_team_id = placement.team_id
            elif placement.placement == 2:
                tournament.runner_up_team_id = placement.team_id
            elif placement.placement == 3:
                tournament.third_place_team_id = placement.team_id
        tournament.status = TournamentStatus.COMPLETED
        tournament.finalized_at = datetime.utcnow()
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return tournament
