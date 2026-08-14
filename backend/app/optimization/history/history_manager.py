from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from app.schemas.schemas import ParticipantFeatures


class HistoryManager:
    def __init__(self, enable: bool = True):
        self.enable = enable
        self.team_history: List[List[str]] = []
        self.role_history: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.pairing_count: Dict[Tuple[str, str], int] = defaultdict(int)

    def record_team(self, team: List[Tuple[ParticipantFeatures, str]]) -> None:
        if not self.enable:
            return
        player_ids = [p.player_id for p, _ in team]
        self.team_history.append(player_ids)
        for p, role in team:
            self.role_history[p.player_id][role] += 1
        for i in range(len(player_ids)):
            for j in range(i + 1, len(player_ids)):
                pair = tuple(sorted([player_ids[i], player_ids[j]]))
                self.pairing_count[pair] += 1

    def get_repeated_pairing_penalty(self, team: List[Tuple[ParticipantFeatures, str]]) -> float:
        if not self.enable:
            return 0.0
        penalty = 0.0
        player_ids = [p.player_id for p, _ in team]
        for i in range(len(player_ids)):
            for j in range(i + 1, len(player_ids)):
                pair = tuple(sorted([player_ids[i], player_ids[j]]))
                count = self.pairing_count.get(pair, 0)
                penalty += count * 5.0
        return penalty

    def get_role_history_penalty(self, player: ParticipantFeatures, role: str) -> float:
        if not self.enable:
            return 0.0
        history = self.role_history.get(player.player_id, {})
        count = history.get(role, 0)
        return count * 3.0

    def get_player_role_distribution(self, player_id: str) -> Dict[str, int]:
        return dict(self.role_history.get(player_id, {}))

    def clear(self) -> None:
        self.team_history.clear()
        self.role_history.clear()
        self.pairing_count.clear()

    def to_dict(self) -> Dict:
        return {
            "team_history": [list(team) for team in self.team_history[-50:]],
            "role_history": {pid: dict(roles) for pid, roles in list(self.role_history.items())[:100]},
            "pairing_count": {f"{a}-{b}": count for (a, b), count in list(self.pairing_count.items())[:100]},
        }
