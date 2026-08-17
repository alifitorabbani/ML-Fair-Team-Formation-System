from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.tournament.models.tournament_models import (
    Tournament,
    KnockoutBracket,
    KnockoutRound,
    KnockoutSlot,
    Match,
    TournamentPlacement,
)
from app.tournament.repositories import (
    TournamentRepository,
    KnockoutBracketRepository,
    KnockoutRoundRepository,
    KnockoutSlotRepository,
    MatchRepository,
    TournamentPlacementRepository,
    MatchResultVersionRepository,
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

    async def generate_bracket(self, tournament_id: str, bracket_type: str, qualified_teams: List[str], seeding: Optional[List[str]] = None) -> KnockoutBracket:
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if not tournament:
            raise ValueError("Tournament not found")
        if tournament.status not in [TournamentStatus.GROUP_FINALIZED, TournamentStatus.KNOCKOUT, TournamentStatus.FINAL, TournamentStatus.TEAMS_LOCKED, TournamentStatus.GROUPS_CONFIGURED]:
            raise ValueError(f"Cannot generate bracket in status {tournament.status}")
        if len(qualified_teams) < 2:
            raise ValueError("At least 2 qualified teams required")
        await self.bracket_repo.delete_by_tournament(tournament_id)
        if seeding:
            ordered = [t for t in seeding if t in qualified_teams]
            remaining = [t for t in qualified_teams if t not in ordered]
            ordered.extend(remaining)
        else:
            ordered = list(qualified_teams)
        bracket = await self.bracket_repo.create(
            {
                "tournament_id": tournament_id,
                "name": f"{bracket_type} Bracket",
                "bracket_type": bracket_type,
                "sort_order": {"UPPER": 1, "LOWER": 2}.get(bracket_type, 99),
            }
        )
        num_teams = len(ordered)
        if num_teams < 2:
            raise ValueError("At least 2 teams required to generate bracket")
        num_rounds = (num_teams - 1).bit_length()
        for round_num in range(1, num_rounds + 1):
            matches_in_round = max(1, num_teams // (2 ** round_num))
            round_obj = await self.round_repo.create(
                {
                    "bracket_id": bracket.id,
                    "round_number": round_num,
                    "round_name": f"Round {round_num}",
                }
            )
            for slot_num in range(1, matches_in_round + 1):
                await self.slot_repo.create(
                    {
                        "round_id": round_obj.id,
                        "slot_number": slot_num,
                        "status": "EMPTY",
                    }
                )
        if num_teams >= 2 and num_rounds > 0:
            rounds = await self.round_repo.get_by_bracket(bracket.id)
            first_round = rounds[0]
            slots = await self.slot_repo.get_by_round(first_round.id)
            matches_to_create = []
            for idx in range(0, num_teams - 1, 2):
                team_a = ordered[idx]
                team_b = ordered[idx + 1]
                slot = slots[idx // 2] if idx // 2 < len(slots) else None
                if slot:
                    slot.team_id = None
                    slot.status = "FILLED"
                    await self.db.flush()
                    bo_format = self._get_bo_format_for_match(bracket.bracket_type, first_round.round_number, rounds)
                    match = await self.match_repo.create(
                        {
                            "tournament_id": tournament_id,
                            "stage": MatchStage.KNOCKOUT,
                            "bracket_id": bracket.id,
                            "round": first_round.round_number,
                            "match_number": slot.slot_number,
                            "scheduled_date": datetime.utcnow().date(),
                            "start_time": datetime.utcnow().time(),
                            "end_time": datetime.utcnow().time(),
                            "team_a_id": team_a,
                            "team_b_id": team_b,
                            "format": bo_format,
                            "status": MatchStatus.SCHEDULED,
                        }
                    )
                    await self.slot_repo.update(slot.id, {"next_match_id": match.id, "next_slot_number": slot.slot_number})
                    matches_to_create.append(match)
        tournament.status = TournamentStatus.KNOCKOUT
        tournament.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(tournament)
        return bracket

    async def populate_initial_round(self, tournament_id: str, bracket_id: str, team_ids: List[str]) -> List[Match]:
        bracket = await self.bracket_repo.get_by_tournament(tournament_id)
        target = next((b for b in bracket if b.id == bracket_id), None)
        if not target:
            raise ValueError("Bracket not found")
        rounds = await self.round_repo.get_by_bracket(bracket_id)
        if not rounds:
            raise ValueError("Bracket has no rounds")
        first_round = rounds[0]
        slots = await self.slot_repo.get_by_round(first_round.id)
        if len(team_ids) < 2:
            raise ValueError("At least 2 teams required")
        matches = []
        for idx in range(0, len(team_ids) - 1, 2):
            team_a = team_ids[idx]
            team_b = team_ids[idx + 1]
            slot = slots[idx // 2] if idx // 2 < len(slots) else None
            if not slot:
                continue
            slot.team_id = None
            slot.status = "FILLED"
            await self.db.flush()
            bo_format = self._get_bo_format_for_match(bracket.bracket_type, first_round.round_number, rounds)
            match = await self.match_repo.create(
                {
                    "tournament_id": tournament_id,
                    "stage": MatchStage.KNOCKOUT,
                    "bracket_id": bracket_id,
                    "round": first_round.round_number,
                    "match_number": slot.slot_number,
                    "scheduled_date": datetime.utcnow().date(),
                    "start_time": datetime.utcnow().time(),
                    "end_time": datetime.utcnow().time(),
                    "team_a_id": team_a,
                    "team_b_id": team_b,
                    "format": bo_format,
                    "status": MatchStatus.SCHEDULED,
                }
            )
            await self.slot_repo.update(slot.id, {"next_match_id": match.id, "next_slot_number": slot.slot_number})
            matches.append(match)
        return matches

    async def advance_winner(self, tournament_id: str, match_id: str) -> Optional[Match]:
        match = await self.match_repo.get_by_id(match_id)
        if not match or match.tournament_id != tournament_id:
            raise ValueError("Match not found")
        if not match.winner_team_id:
            raise ValueError("Match has no winner")
        winner_id = match.winner_team_id
        loser_id = match.team_a_id if match.team_b_id == winner_id else match.team_b_id
        if match.bracket_id:
            bracket = await self.bracket_repo.get_by_tournament(tournament_id)
            current_bracket = next((b for b in bracket if b.id == match.bracket_id), None)
            if current_bracket:
                await self._advance_in_bracket(match, winner_id, loser_id, current_bracket)
        if match.round:
            rounds = await self.round_repo.get_by_bracket(match.bracket_id) if match.bracket_id else []
            current_round = next((r for r in rounds if r.round_number == match.round), None)
            if current_round:
                await self._advance_to_next_round(match, winner_id, loser_id, current_round, rounds)
        await self._maybe_create_grand_final(tournament_id)
        tournament = await self.tournament_repo.get_by_id(tournament_id)
        if tournament and tournament.status == TournamentStatus.KNOCKOUT:
            tournament.status = TournamentStatus.FINAL
            tournament.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(tournament)
        return match

    async def _maybe_create_grand_final(self, tournament_id: str):
        brackets = await self.bracket_repo.get_by_tournament(tournament_id)
        upper_bracket = next((b for b in brackets if b.bracket_type == BracketType.UPPER), None)
        lower_bracket = next((b for b in brackets if b.bracket_type == BracketType.LOWER), None)
        if not upper_bracket or not lower_bracket:
            return
        existing_grand_final = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        grand_final_exists = any(m.bracket_id is None and m.round is None for m in existing_grand_final)
        if grand_final_exists:
            return
        upper_winner = self._get_bracket_winner(tournament_id, upper_bracket.id)
        lower_winner = self._get_bracket_winner(tournament_id, lower_bracket.id)
        if not upper_winner or not lower_winner:
            return
        await self.match_repo.create(
            {
                "tournament_id": tournament_id,
                "stage": MatchStage.KNOCKOUT,
                "bracket_id": None,
                "round": None,
                "match_number": 1,
                "scheduled_date": datetime.utcnow().date(),
                "start_time": datetime.utcnow().time(),
                "end_time": datetime.utcnow().time(),
                "team_a_id": upper_winner,
                "team_b_id": lower_winner,
                "format": BOFormat.BO7.value,
                "status": MatchStatus.SCHEDULED,
            }
        )

    async def _get_bracket_winner(self, tournament_id: str, bracket_id: str) -> Optional[str]:
        bracket = await self.bracket_repo.get_by_tournament(tournament_id)
        target = next((b for b in bracket if b.id == bracket_id), None)
        if not target:
            return None
        rounds = await self.round_repo.get_by_bracket(bracket_id)
        if not rounds:
            return None
        last_round = rounds[-1]
        slots = await self.slot_repo.get_by_round(last_round.id)
        for slot in slots:
            if slot.team_id and slot.status == "FILLED":
                return slot.team_id
        return None

    async def _advance_in_bracket(self, match: Match, winner_id: str, loser_id: str, bracket: KnockoutBracket):
        if bracket.bracket_type == BracketType.UPPER:
            await self._move_loser_to_bracket(match.tournament_id, loser_id, BracketType.LOWER)
        elif bracket.bracket_type == BracketType.LOWER:
            pass

    async def _move_loser_to_bracket(self, tournament_id: str, team_id: str, bracket_type: str):
        brackets = await self.bracket_repo.get_by_tournament(tournament_id)
        target_bracket = next((b for b in brackets if b.bracket_type == bracket_type), None)
        if not target_bracket:
            return
        rounds = await self.round_repo.get_by_bracket(target_bracket.id)
        if not rounds:
            return
        for round_obj in rounds:
            slots = await self.slot_repo.get_by_round(round_obj.id)
            for slot in slots:
                if slot.status == "EMPTY" and slot.team_id is None:
                    slot.team_id = team_id
                    slot.status = "FILLED"
                    await self.db.flush()
                    return

    async def _advance_to_next_round(self, match: Match, winner_id: str, loser_id: str, current_round: KnockoutRound, all_rounds: List[KnockoutRound]):
        next_round_num = current_round.round_number + 1
        next_round = next((r for r in all_rounds if r.round_number == next_round_num), None)
        if not next_round:
            return
        slots = await self.slot_repo.get_by_round(next_round.id)
        target_slot = None
        for slot in slots:
            if slot.team_id is None and slot.status == "EMPTY":
                target_slot = slot
                break
        if not target_slot:
            return
        target_slot.team_id = winner_id
        target_slot.status = "FILLED"
        await self.db.flush()
        if len(slots) >= 2:
            for slot in slots:
                if slot.team_id is not None and slot.status == "FILLED":
                    opponents = [s for s in slots if s.team_id is not None and s.id != slot.id and s.status == "FILLED"]
                    if opponents:
                        team_a = slot.team_id
                        team_b = opponents[0].team_id
                        bo_format = self._get_bo_format_for_match(match.bracket_id, next_round.round_number, all_rounds)
                        next_match = await self.match_repo.create(
                            {
                                "tournament_id": match.tournament_id,
                                "stage": MatchStage.KNOCKOUT,
                                "bracket_id": match.bracket_id,
                                "round": next_round.round_number,
                                "match_number": slot.slot_number,
                                "scheduled_date": datetime.utcnow().date(),
                                "start_time": datetime.utcnow().time(),
                                "end_time": datetime.utcnow().time(),
                                "team_a_id": team_a,
                                "team_b_id": team_b,
                                "format": bo_format,
                                "status": MatchStatus.SCHEDULED,
                            }
                        )
                        await self.slot_repo.update(slot.id, {"next_match_id": next_match.id, "next_slot_number": slot.slot_number})
                        break

    def _get_bo_format_for_match(self, bracket_id: str, round_number: int, all_rounds: List[KnockoutRound]) -> str:
        max_round = max(r.round_number for r in all_rounds) if all_rounds else 1
        if round_number == max_round:
            if max_round == 1:
                return BOFormat.BO5.value
            return BOFormat.BO5.value
        return BOFormat.BO3.value

    async def get_bracket(self, tournament_id: str) -> List[Dict[str, Any]]:
        brackets = await self.bracket_repo.get_by_tournament(tournament_id)
        all_matches = await self.match_repo.get_by_tournament(tournament_id, MatchStage.KNOCKOUT)
        results = []
        for bracket in brackets:
            rounds = await self.round_repo.get_by_bracket(bracket.id)
            rounds_data = []
            for round_obj in rounds:
                slots = await self.slot_repo.get_by_round(round_obj.id)
                slots_data = []
                for slot in slots:
                    slot_matches = [m for m in all_matches if m.bracket_id == bracket.id and m.round == round_obj.round_number and (m.team_a_id == slot.team_id or m.team_b_id == slot.team_id)]
                    match = slot_matches[0] if slot_matches else None
                    slots_data.append(
                        {
                            "id": slot.id,
                            "slot_number": slot.slot_number,
                            "team_id": slot.team_id,
                            "next_match_id": slot.next_match_id,
                            "next_slot_number": slot.next_slot_number,
                            "status": slot.status,
                            "match": {
                                "id": match.id if match else None,
                                "team_a_id": match.team_a_id if match else None,
                                "team_b_id": match.team_b_id if match else None,
                                "winner_team_id": match.winner_team_id if match else None,
                                "status": match.status if match else None,
                                "format": match.format if match else None,
                                "score_a": match.score_a if match else None,
                                "score_b": match.score_b if match else None,
                            } if match else None,
                        }
                    )
                rounds_data.append(
                    {
                        "id": round_obj.id,
                        "round_number": round_obj.round_number,
                        "round_name": round_obj.round_name,
                        "slots": slots_data,
                    }
                )
            results.append(
                {
                    "id": bracket.id,
                    "name": bracket.name,
                    "bracket_type": bracket.bracket_type,
                    "sort_order": bracket.sort_order,
                    "rounds": rounds_data,
                }
            )
        return results

    async def set_third_place(self, tournament_id: str, team_id: str, source: str = "MANUAL") -> TournamentPlacement:
        existing = await self.placement_repo.get_by_tournament_and_team(tournament_id, team_id)
        if existing:
            existing.placement = 3
            existing.source = source
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        return await self.placement_repo.create(
            {
                "tournament_id": tournament_id,
                "team_id": team_id,
                "placement": 3,
                "source": source,
            }
        )
