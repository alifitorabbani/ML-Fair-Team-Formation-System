from typing import List, Tuple
from app.schemas.schemas import ParticipantFeatures
from app.config.settings import settings


REQUIRED_LANES = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]


class ParticipantSelector:
    def __init__(
        self,
        participants: List[ParticipantFeatures],
        num_teams: int,
    ):
        self.participants = participants
        self.num_teams = num_teams
        self.slots_needed = num_teams * 5

    def _get_effective_rank(self, p: ParticipantFeatures) -> float:
        rank_order = {
            "Warrior": 1, "Elite": 2, "Master": 3, "Grandmaster": 4,
            "Epic": 5, "Legend": 6, "Mythic": 7,
            "Mythical Honor": 8, "Mythical Glory": 9, "Mythical Immortal": 10,
        }
        current = rank_order.get(p.current_rank, 0)
        highest = rank_order.get(p.highest_rank, 0)
        return (current + highest) / 2.0

    def _select_with_lane_diversity(self) -> List[ParticipantFeatures]:
        if len(self.participants) <= self.slots_needed:
            return list(self.participants)

        sorted_pool = sorted(
            self.participants,
            key=lambda p: (
                p.role_flexibility_score,
                self._get_effective_rank(p),
                p.skill_score,
                p.player_id,
            ),
            reverse=True,
        )

        lane_pools: dict = {lane: [] for lane in REQUIRED_LANES}
        for p in sorted_pool:
            for lane in [p.primary_lane, p.secondary_lane]:
                if lane in lane_pools:
                    lane_pools[lane].append(p)

        selected: List[ParticipantFeatures] = []
        selected_ids = set()
        lane_counts = {lane: 0 for lane in REQUIRED_LANES}

        for lane in REQUIRED_LANES:
            target = self.num_teams
            for p in lane_pools[lane]:
                if lane_counts[lane] >= target:
                    break
                if p.player_id not in selected_ids:
                    selected.append(p)
                    selected_ids.add(p.player_id)
                    lane_counts[lane] += 1

        remaining = self.slots_needed - len(selected)
        if remaining > 0:
            for p in sorted_pool:
                if remaining <= 0:
                    break
                if p.player_id not in selected_ids:
                    selected.append(p)
                    selected_ids.add(p.player_id)
                    remaining -= 1

        if len(selected) < self.slots_needed:
            for p in sorted_pool:
                if len(selected) >= self.slots_needed:
                    break
                if p.player_id not in selected_ids:
                    selected.append(p)
                    selected_ids.add(p.player_id)

        return selected

    def select_optimal_subset(self) -> Tuple[List[ParticipantFeatures], List[ParticipantFeatures]]:
        selected = self._select_with_lane_diversity()
        selected_ids = {p.player_id for p in selected}
        not_selected = [p for p in self.participants if p.player_id not in selected_ids]
        return selected, not_selected
