from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import (
    Tournament,
    KnockoutBracket,
    KnockoutRound,
    KnockoutSlot,
    Match,
    TournamentPlacement,
    BracketStanding,
    TournamentGroup,
    GroupStanding,
)
from app.tournament.repositories import (
    TournamentRepository,
    KnockoutBracketRepository,
    KnockoutRoundRepository,
    KnockoutSlotRepository,
    MatchRepository,
    TournamentPlacementRepository,
    MatchResultVersionRepository,
    BracketStandingRepository,
)
from app.tournament.constants import (
    TournamentStatus,
    MatchStatus,
    MatchStage,
    BracketType,
    ThirdPlaceMode,
    BracketLoserRule,
    BOFormat,
)


# Exact 8-team double elimination bracket definition
# Each match: (match_number, bracket_label, round_label, format, winner_next, loser_next, elimination, placement_on_win, placement_on_lose)
BRACKET_DEFINITION = {
    1: {
        "match_number": 1,
        "bracket": "UPPER",
        "round": "UPPER_ROUND_1",
        "format": BOFormat.BO3,
        "label": "Upper Round 1",
        "team_a_seed": 1,
        "team_b_seed": 4,
        "winner_next": 5,
        "loser_next": 6,
        "elimination_on_lose": False,
    },
    2: {
        "match_number": 2,
        "bracket": "UPPER",
        "round": "UPPER_ROUND_1",
        "format": BOFormat.BO3,
        "label": "Upper Round 1",
        "team_a_seed": 2,
        "team_b_seed": 3,
        "winner_next": 5,
        "loser_next": 7,
        "elimination_on_lose": False,
    },
    3: {
        "match_number": 3,
        "bracket": "LOWER",
        "round": "LOWER_ROUND_1",
        "format": BOFormat.BO3,
        "label": "Lower Round 1",
        "team_a_seed": 5,
        "team_b_seed": 8,
        "winner_next": 6,
        "loser_next": None,
        "elimination_on_lose": True,
    },
    4: {
        "match_number": 4,
        "bracket": "LOWER",
        "round": "LOWER_ROUND_1",
        "format": BOFormat.BO3,
        "label": "Lower Round 1",
        "team_a_seed": 6,
        "team_b_seed": 7,
        "winner_next": 7,
        "loser_next": None,
        "elimination_on_lose": True,
    },
    5: {
        "match_number": 5,
        "bracket": "UPPER",
        "round": "UPPER_FINAL",
        "format": BOFormat.BO5,
        "label": "Upper Final",
        "team_a_source": "winner_1",
        "team_b_source": "winner_2",
        "winner_next": 10,
        "loser_next": 9,
        "elimination_on_lose": False,
        "placement_on_win": "UPPER_CHAMPION",
    },
    6: {
        "match_number": 6,
        "bracket": "LOWER",
        "round": "LOWER_ROUND_2",
        "format": BOFormat.BO3,
        "label": "Lower Round 2",
        "team_a_source": "winner_3",
        "team_b_source": "loser_1",
        "winner_next": 8,
        "loser_next": None,
        "elimination_on_lose": True,
    },
    7: {
        "match_number": 7,
        "bracket": "LOWER",
        "round": "LOWER_ROUND_2",
        "format": BOFormat.BO3,
        "label": "Lower Round 2",
        "team_a_source": "winner_4",
        "team_b_source": "loser_2",
        "winner_next": 8,
        "loser_next": None,
        "elimination_on_lose": True,
    },
    8: {
        "match_number": 8,
        "bracket": "LOWER",
        "round": "LOWER_SEMIFINAL",
        "format": BOFormat.BO3,
        "label": "Lower Bracket Final / Lower Semifinal",
        "team_a_source": "winner_6",
        "team_b_source": "winner_7",
        "winner_next": 9,
        "loser_next": None,
        "elimination_on_lose": True,
    },
    9: {
        "match_number": 9,
        "bracket": "LOWER",
        "round": "LOWER_FINAL",
        "format": BOFormat.BO5,
        "label": "Lower Final",
        "team_a_source": "winner_8",
        "team_b_source": "loser_5",
        "winner_next": 10,
        "loser_next": None,
        "elimination_on_lose": False,
        "placement_on_lose": "THIRD_PLACE",
    },
    10: {
        "match_number": 10,
        "bracket": "GRAND_FINAL",
        "round": "GRAND_FINAL",
        "format": BOFormat.BO7,
        "label": "Grand Final",
        "team_a_source": "upper_champion",
        "team_b_source": "winner_9",
        "winner_next": None,
        "loser_next": None,
        "elimination_on_lose": False,
        "placement_on_win": "CHAMPION",
        "placement_on_lose": "RUNNER_UP",
    },
}


class BracketService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tournament_repo = TournamentRepository(db)
        self.bracket_repo = KnockoutBracketRepository(db)
        self.round_repo = KnockoutRoundRepository(db)
        self.slot_repo = KnockoutSlotRepository(db)
        self.match_repo = MatchRepository(db)
        self.placement_repo = TournamentPlacementRepository(db)
        self.result_version_repo = MatchResultVersionRepository(db)
        self.bracket_standing_repo = BracketStandingRepository(db)

    async def generate_bracket(self, tournament_id: str, qualified_teams: Optional[List[str]] = None, seeding: Optional[List[str]] = None, populate_matches: bool = True) -> Dict[str, Any]:
        """Generate exact 8-team double elimination bracket template."""
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")

        # Clear existing bracket data
        await self.bracket_repo.delete_by_tournament(tournament_id)
        
        # Create bracket structures for visualization
        upper_bracket = await self.bracket_repo.create({
            "tournament_id": tournament_id,
            "name": "Upper Bracket",
            "bracket_type": BracketType.UPPER,
            "sort_order": 1,
        })
        
        lower_bracket = await self.bracket_repo.create({
            "tournament_id": tournament_id,
            "name": "Lower Bracket",
            "bracket_type": BracketType.LOWER,
            "sort_order": 2,
        })

        # Create rounds and slots for visualization
        # Upper bracket: Round 1 (2 matches), Upper Final (1 match)
        upper_rounds = {}
        for round_name, match_nums in [
            ("UPPER_ROUND_1", [1, 2]),
            ("UPPER_FINAL", [5]),
        ]:
            round_obj = await self.round_repo.create({
                "bracket_id": upper_bracket.id,
                "round_number": match_nums[0],
                "round_name": round_name,
            })
            for slot_num in range(1, len(match_nums) + 1):
                await self.slot_repo.create({
                    "round_id": round_obj.id,
                    "slot_number": slot_num,
                    "status": "EMPTY",
                })
            upper_rounds[round_name] = round_obj

        # Lower bracket: Round 1 (2 matches), Round 2 (2 matches), Lower Semifinal (1 match)
        lower_rounds = {}
        for round_name, match_nums in [
            ("LOWER_ROUND_1", [3, 4]),
            ("LOWER_ROUND_2", [6, 7]),
            ("LOWER_SEMIFINAL", [8]),
        ]:
            round_obj = await self.round_repo.create({
                "bracket_id": lower_bracket.id,
                "round_number": match_nums[0],
                "round_name": round_name,
            })
            for slot_num in range(1, len(match_nums) + 1):
                await self.slot_repo.create({
                    "round_id": round_obj.id,
                    "slot_number": slot_num,
                    "status": "EMPTY",
                })
            lower_rounds[round_name] = round_obj

        # Create all 10 matches with proper routing
        matches = {}
        for match_num, match_def in BRACKET_DEFINITION.items():
            # Determine bracket_id and round_id
            if match_def["bracket"] == "UPPER":
                bracket_id = upper_bracket.id
                round_obj = upper_rounds.get(match_def["round"])
            elif match_def["bracket"] == "LOWER":
                bracket_id = lower_bracket.id
                round_obj = lower_rounds.get(match_def["round"])
            else:  # GRAND_FINAL
                bracket_id = None
                round_obj = None

            # Determine initial teams and sources
            team_a_id = None
            team_b_id = None
            participant_source_a = None
            participant_source_b = None
            
            if "team_a_seed" in match_def:
                if match_def["bracket"] == "UPPER":
                    idx = match_def["team_a_seed"] - 1
                    if qualified_teams and len(qualified_teams) >= 8:
                        team_a_id = qualified_teams[idx]
                    else:
                        participant_source_a = f"FINAL_STANDINGS_RANK_{match_def['team_a_seed']}"
                else:
                    idx = match_def["team_a_seed"] - 5
                    if qualified_teams and len(qualified_teams) >= 8:
                        team_a_id = qualified_teams[idx]
                    else:
                        participant_source_a = f"FINAL_STANDINGS_RANK_{match_def['team_a_seed']}"
            
            if "team_b_seed" in match_def:
                if match_def["bracket"] == "UPPER":
                    idx = match_def["team_b_seed"] - 1
                    if qualified_teams and len(qualified_teams) >= 8:
                        team_b_id = qualified_teams[idx]
                    else:
                        participant_source_b = f"FINAL_STANDINGS_RANK_{match_def['team_b_seed']}"
                else:
                    idx = match_def["team_b_seed"] - 5
                    if qualified_teams and len(qualified_teams) >= 8:
                        team_b_id = qualified_teams[idx]
                    else:
                        participant_source_b = f"FINAL_STANDINGS_RANK_{match_def['team_b_seed']}"

            if "team_a_source" in match_def:
                participant_source_a = match_def["team_a_source"]
            if "team_b_source" in match_def:
                participant_source_b = match_def["team_b_source"]

            match = await self.match_repo.create({
                "tournament_id": tournament_id,
                "stage": MatchStage.KNOCKOUT,
                "bracket_id": bracket_id,
                "round": round_obj.round_number if round_obj else None,
                "match_number": match_num,
                "scheduled_date": datetime.utcnow().date(),
                "start_time": datetime.utcnow().time(),
                "end_time": datetime.utcnow().time(),
                "team_a_id": team_a_id,
                "team_b_id": team_b_id,
                "participant_source_a": participant_source_a,
                "participant_source_b": participant_source_b,
                "format": match_def["format"],
                "status": MatchStatus.SCHEDULED,
                "winner_team_id": None,
                "next_match_id": None,
                "loser_next_match_id": None,
            })
            matches[match_num] = match

        # Link matches via next_match_id and loser_next_match_id
        for match_num, match_def in BRACKET_DEFINITION.items():
            match = matches[match_num]
            if match_def.get("winner_next"):
                match.next_match_id = matches[match_def["winner_next"]].id
            if match_def.get("loser_next"):
                match.loser_next_match_id = matches[match_def["loser_next"]].id
            await self.db.flush()

        # Update tournament status
        tournament.status = TournamentStatus.KNOCKOUT
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)

        return {
            "tournament": tournament,
            "upper_bracket": upper_bracket,
            "lower_bracket": lower_bracket,
            "matches": matches,
        }

    async def resolve_bracket_from_standings(self, tournament_id: str) -> Dict[str, Any]:
        """Resolve bracket participants from final group standings."""
        from sqlalchemy import select
        from app.tournament.models.tournament_models import GroupStanding
        
        # Get all group standings sorted by rank
        stmt = (
            select(GroupStanding)
            .where(GroupStanding.group_id.in_(
                select(TournamentGroup.id).where(TournamentGroup.tournament_id == tournament_id)
            ))
            .order_by(GroupStanding.rank.asc(), GroupStanding.points.desc())
        )
        result = await self.db.execute(stmt)
        standings = result.scalars().all()
        
        if len(standings) < 8:
            raise ValueError(f"Need at least 8 teams in standings to resolve bracket, got {len(standings)}")
        
        # Build rank -> team_id mapping from standings
        rank_to_team = {}
        for s in standings:
            if s.rank is not None and s.team_id:
                rank_to_team[s.rank] = s.team_id
        
        # Get all knockout matches
        matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        match_map = {m.match_number: m for m in matches if m.match_number is not None}
        
        # Resolve initial upper bracket matches (1-2)
        # Match 1: Rank 1 vs Rank 4
        if 1 in match_map:
            m = match_map[1]
            m.team_a_id = rank_to_team.get(1)
            m.team_b_id = rank_to_team.get(4)
            m.participant_source_a = f"FINAL_STANDINGS_RANK_1"
            m.participant_source_b = f"FINAL_STANDINGS_RANK_4"
        
        # Match 2: Rank 2 vs Rank 3
        if 2 in match_map:
            m = match_map[2]
            m.team_a_id = rank_to_team.get(2)
            m.team_b_id = rank_to_team.get(3)
            m.participant_source_a = f"FINAL_STANDINGS_RANK_2"
            m.participant_source_b = f"FINAL_STANDINGS_RANK_3"
        
        # Resolve initial lower bracket matches (3-4)
        # Match 3: Rank 5 vs Rank 8
        if 3 in match_map:
            m = match_map[3]
            m.team_a_id = rank_to_team.get(5)
            m.team_b_id = rank_to_team.get(8)
            m.participant_source_a = f"FINAL_STANDINGS_RANK_5"
            m.participant_source_b = f"FINAL_STANDINGS_RANK_8"
        
        # Match 4: Rank 6 vs Rank 7
        if 4 in match_map:
            m = match_map[4]
            m.team_a_id = rank_to_team.get(6)
            m.team_b_id = rank_to_team.get(7)
            m.participant_source_a = f"FINAL_STANDINGS_RANK_6"
            m.participant_source_b = f"FINAL_STANDINGS_RANK_7"
        
        await self.db.flush()
        
        return {
            "resolved_matches": [match_map.get(i) for i in range(1, 5) if i in match_map],
            "standings_used": len(standings),
        }

    async def advance_winner(self, tournament_id: str, match_id: str) -> Optional[Match]:
        """Advance winner and loser from a completed match to their next matches."""
        match = await self.match_repo.get_by_id(match_id)
        if not match or match.tournament_id != tournament_id:
            raise ValueError("Match not found")
        if match.status != MatchStatus.COMPLETED:
            raise ValueError("Match must be completed before advancing")
        if not match.winner_team_id:
            raise ValueError("Match has no winner")

        winner_id = match.winner_team_id
        loser_id = match.team_a_id if match.team_b_id == winner_id else match.team_b_id
        match_num = match.match_number

        if match_num not in BRACKET_DEFINITION:
            raise ValueError(f"Unknown match number: {match_num}")

        match_def = BRACKET_DEFINITION[match_num]

        # Validate no team is in two active matches
        await self._validate_no_duplicate_active_team(tournament_id, winner_id, exclude_match_id=match.id)
        await self._validate_no_duplicate_active_team(tournament_id, loser_id, exclude_match_id=match.id)

        # Validate eliminated teams don't advance
        if match_def.get("elimination_on_lose"):
            await self._mark_team_eliminated(tournament_id, loser_id)
        else:
            # Advance loser to next match if specified
            if match_def.get("loser_next") and match.loser_next_match_id:
                next_match = await self.match_repo.get_by_id(match.loser_next_match_id)
                if next_match:
                    # Check if the next match is ready to receive the loser
                    if next_match.team_a_id is None:
                        next_match.team_a_id = loser_id
                    elif next_match.team_b_id is None:
                        next_match.team_b_id = loser_id
                    else:
                        # Both slots filled, shouldn't happen with proper bracket
                        pass
                    await self.db.flush()

        # Advance winner to next match if specified
        if match_def.get("winner_next") and match.next_match_id:
            next_match = await self.match_repo.get_by_id(match.next_match_id)
            if next_match:
                if next_match.team_a_id is None:
                    next_match.team_a_id = winner_id
                elif next_match.team_b_id is None:
                    next_match.team_b_id = winner_id
                else:
                    # Both slots filled, shouldn't happen with proper bracket
                    pass
                await self.db.flush()

        # Handle placements
        if match_def.get("placement_on_win") == "CHAMPION":
            await self._set_placement(tournament_id, winner_id, 1, "CHAMPION")
            tournament = await self.tournament_repo.get_by_id(tournament_id)
            if tournament:
                tournament.champion_team_id = winner_id
                tournament.status = TournamentStatus.COMPLETED
                tournament.updated_at = datetime.utcnow()
                await self.db.flush()
        elif match_def.get("placement_on_lose") == "RUNNER_UP":
            await self._set_placement(tournament_id, loser_id, 2, "RUNNER_UP")
            tournament = await self.tournament_repo.get_by_id(tournament_id)
            if tournament:
                tournament.runner_up_team_id = loser_id
                tournament.status = TournamentStatus.COMPLETED
                tournament.updated_at = datetime.utcnow()
                await self.db.flush()
        elif match_def.get("placement_on_lose") == "THIRD_PLACE":
            await self._set_placement(tournament_id, loser_id, 3, "THIRD_PLACE")
            tournament = await self.tournament_repo.get_by_id(tournament_id)
            if tournament:
                tournament.third_place_team_id = loser_id
                await self.db.flush()
        elif match_def.get("placement_on_win") == "UPPER_CHAMPION":
            # Upper champion waits in grand final, no placement yet
            pass

        # Mark match as completed
        match.status = MatchStatus.COMPLETED
        match.winner_team_id = winner_id
        match.score_a = match.score_a or 0
        match.score_b = match.score_b or 0
        await self.db.flush()
        await self.db.refresh(match)

        return match

    async def reset_bracket(self, tournament_id: str) -> bool:
        """Reset all bracket matches and placements."""
        # Get all knockout matches
        matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        
        # Reset all matches
        for match in matches:
            match.winner_team_id = None
            match.score_a = None
            match.score_b = None
            match.kills_a = None
            match.kills_b = None
            match.deaths_a = None
            match.deaths_b = None
            match.status = MatchStatus.SCHEDULED
            match.next_match_id = None
            match.loser_next_match_id = None
            # Keep initial teams for matches 1-4
            if match.match_number <= 4:
                pass  # Keep initial seeding
            else:
                match.team_a_id = None
                match.team_b_id = None
            await self.db.flush()

        # Clear placements
        placements = await self.placement_repo.get_by_tournament(tournament_id)
        for placement in placements:
            await self.db.delete(placement)
        await self.db.flush()

        # Reset tournament fields
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if tournament:
            tournament.champion_team_id = None
            tournament.runner_up_team_id = None
            tournament.third_place_team_id = None
            tournament.status = TournamentStatus.KNOCKOUT
            tournament.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(tournament)

        return True

    async def get_bracket(self, tournament_id: str) -> Dict[str, Any]:
        """Get bracket data for frontend visualization."""
        all_matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        
        upper_matches = []
        lower_matches = []
        grand_final = None
        lower_final = None
        
        for m in all_matches:
            if m.match_number is None:
                continue
            
            match_data = {
                "id": m.id,
                "match_number": m.match_number,
                "team_a_id": m.team_a_id,
                "team_b_id": m.team_b_id,
                "winner_team_id": m.winner_team_id,
                "status": m.status,
                "format": m.format,
                "score_a": m.score_a,
                "score_b": m.score_b,
                "round": m.round,
                "next_match_id": m.next_match_id,
                "loser_next_match_id": m.loser_next_match_id,
            }
            
            if m.match_number <= 2:
                match_data["bracket_type"] = "UPPER"
                match_data["round"] = 1
                upper_matches.append(match_data)
            elif m.match_number == 5:
                match_data["bracket_type"] = "UPPER"
                match_data["is_upper_final"] = True
                match_data["round"] = 2
                upper_matches.append(match_data)
            elif 3 <= m.match_number <= 4:
                match_data["bracket_type"] = "LOWER"
                match_data["round"] = 1
                lower_matches.append(match_data)
            elif 6 <= m.match_number <= 7:
                match_data["bracket_type"] = "LOWER"
                match_data["round"] = 2
                lower_matches.append(match_data)
            elif m.match_number == 8:
                match_data["bracket_type"] = "LOWER"
                match_data["is_lower_final"] = True
                match_data["round"] = 3
                lower_matches.append(match_data)
            elif m.match_number == 9:
                match_data["bracket_type"] = "LOWER"
                match_data["is_lower_final"] = True
                lower_final = match_data
            elif m.match_number == 10:
                match_data["bracket_type"] = "GRAND_FINAL"
                match_data["is_grand_final"] = True
                grand_final = match_data
        
        # Sort matches by match_number
        upper_matches.sort(key=lambda x: x.match_number)
        lower_matches.sort(key=lambda x: x.match_number)
        
        return {
            "upper_matches": upper_matches,
            "lower_matches": lower_matches,
            "grand_final": grand_final,
            "lower_final": lower_final,
        }

    async def _validate_no_duplicate_active_team(self, tournament_id: str, team_id: str, exclude_match_id: str):
        """Ensure a team is not in multiple active (non-completed) matches."""
        if not team_id:
            return
        matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        active_matches = [m for m in matches if m.status != MatchStatus.COMPLETED and m.id != exclude_match_id]
        for m in active_matches:
            if m.team_a_id == team_id or m.team_b_id == team_id:
                raise ValueError(f"Team {team_id} is already in active match {m.match_number}")

    async def _mark_team_eliminated(self, tournament_id: str, team_id: str):
        """Mark a team as eliminated (no further matches)."""
        # In this system, eliminated teams just don't get routed to any next match
        # We could add an ELIMINATED status to tournament_teams if needed
        pass

    async def _set_placement(self, tournament_id: str, team_id: str, placement: int, source: str):
        """Set team placement."""
        existing = await self.placement_repo.get_by_tournament_and_team(tournament_id, team_id)
        if existing:
            existing.placement = placement
            existing.source = source
            await self.db.flush()
            await self.db.refresh(existing)
        else:
            await self.placement_repo.create({
                "tournament_id": tournament_id,
                "team_id": team_id,
                "placement": placement,
                "source": source,
            })

    async def get_match(self, tournament_id: str, match_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific match by match number."""
        matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        for m in matches:
            if m.match_number == match_number:
                return {
                    "id": m.id,
                    "match_number": m.match_number,
                    "bracket": m.bracket.bracket_type if m.bracket else "GRAND_FINAL",
                    "round": m.round,
                    "format": m.format,
                    "team_a_id": m.team_a_id,
                    "team_b_id": m.team_b_id,
                    "winner_team_id": m.winner_team_id,
                    "status": m.status,
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "next_match_id": m.next_match_id,
                    "loser_next_match_id": m.loser_next_match_id,
                }
        return None

    async def update_match_result(self, tournament_id: str, match_number: int, score_a: int, score_b: int) -> Optional[Match]:
        """Update match result and validate BO format."""
        matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        match = None
        for m in matches:
            if m.match_number == match_number:
                match = m
                break
        
        if not match:
            raise ValueError(f"Match {match_number} not found")
        
        # Validate BO format
        bo_format = match.format
        if bo_format == BOFormat.BO3:
            valid_scores = [(2, 0), (2, 1), (0, 2), (1, 2)]
        elif bo_format == BOFormat.BO5:
            valid_scores = [(3, 0), (3, 1), (3, 2), (0, 3), (1, 3), (2, 3)]
        elif bo_format == BOFormat.BO7:
            valid_scores = [(4, 0), (4, 1), (4, 2), (4, 3), (0, 4), (1, 4), (2, 4), (3, 4)]
        else:
            raise ValueError(f"Unknown BO format: {bo_format}")
        
        if (score_a, score_b) not in valid_scores:
            raise ValueError(f"Invalid score {score_a}-{score_b} for {bo_format}")
        
        # Determine winner
        if score_a > score_b:
            match.winner_team_id = match.team_a_id
        elif score_b > score_a:
            match.winner_team_id = match.team_b_id
        else:
            raise ValueError("Score cannot be tied")
        
        match.score_a = score_a
        match.score_b = score_b
        match.status = MatchStatus.COMPLETED
        await self.db.flush()
        await self.db.refresh(match)
        
        return match

    async def get_standings(self, tournament_id: str) -> List[Dict[str, Any]]:
        """Get tournament standings with placements."""
        placements = await self.placement_repo.get_by_tournament(tournament_id)
        placement_map = {p.team_id: p.placement for p in placements}
        
        # Get all teams
        from app.tournament.models.tournament_models import TournamentTeam
        from sqlalchemy import select
        stmt = select(TournamentTeam).where(TournamentTeam.tournament_id == tournament_id)
        result = await self.db.execute(stmt)
        teams = result.scalars().all()
        
        standings = []
        for team in teams:
            placement = placement_map.get(team.team_id)
            if placement:
                status = self._placement_to_status(placement)
            else:
                status = "ACTIVE"
            
            standings.append({
                "team_id": team.team_id,
                "team_name": team.team_name_snapshot,
                "seed": team.seed,
                "placement": placement,
                "status": status,
            })
        
        # Sort by placement (None last), then by seed
        standings.sort(key=lambda x: (x["placement"] is None, x["placement"] or 999, x["seed"] or 999))
        
        return standings

    def _placement_to_status(self, placement: Optional[int]) -> str:
        if placement == 1:
            return "CHAMPION"
        elif placement == 2:
            return "RUNNER_UP"
        elif placement == 3:
            return "THIRD_PLACE"
        elif placement is not None:
            return f"PLACED_{placement}"
        return "ACTIVE"

    async def recalculate_bracket_standings(self, tournament_id: str):
        """Recalculate bracket points for all teams in the tournament."""
        # Get all completed knockout matches
        matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        completed_matches = [m for m in matches if m.status == MatchStatus.COMPLETED and m.winner_team_id]
        
        # Get all teams that participated in bracket
        team_ids = set()
        for m in matches:
            if m.team_a_id:
                team_ids.add(m.team_a_id)
            if m.team_b_id:
                team_ids.add(m.team_b_id)
        
        # Calculate bracket points
        bracket_points = {}
        for team_id in team_ids:
            bracket_points[team_id] = {"points": 0, "wins": 0, "losses": 0}
        
        for match in completed_matches:
            if not match.winner_team_id:
                continue
            winner_id = match.winner_team_id
            loser_id = match.team_a_id if match.team_b_id == winner_id else match.team_b_id
            
            if winner_id in bracket_points:
                bracket_points[winner_id]["points"] += 1
                bracket_points[winner_id]["wins"] += 1
            if loser_id in bracket_points:
                bracket_points[loser_id]["losses"] += 1
        
        # Save to database
        for team_id, stats in bracket_points.items():
            await self.bracket_standing_repo.create_or_update({
                "tournament_id": tournament_id,
                "team_id": team_id,
                "points": stats["points"],
                "wins": stats["wins"],
                "losses": stats["losses"],
            })
