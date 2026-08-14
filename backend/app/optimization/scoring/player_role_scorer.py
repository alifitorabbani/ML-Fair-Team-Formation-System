from typing import Dict, List, Tuple
from app.optimization.config.role_config import RoleCompatibilityMatrix, OptimizationConfig
from app.optimization.engines.role_compatibility_engine import RoleCompatibilityEngine
from app.schemas.schemas import ParticipantFeatures


class PlayerRoleScorer:
    def __init__(self, config: OptimizationConfig, engine: RoleCompatibilityEngine):
        self.config = config
        self.engine = engine

    def score_player_for_role(self, player: ParticipantFeatures, role: str) -> float:
        preference = self._preference_score(player, role)
        compatibility = self.engine._calculate_score(player, role)
        skill = player.skill_score / 100.0
        return round(
            self.config.scoring_weights.role_preference * preference +
            self.config.scoring_weights.role_compatibility * compatibility +
            self.config.scoring_weights.skill_balance * skill,
            2
        )

    def _preference_score(self, player: ParticipantFeatures, role: str) -> float:
        if role == player.primary_lane:
            return 1.0
        if role == player.secondary_lane:
            return 1.0
        return 0.0

    def rank_players_for_role(self, players: List[ParticipantFeatures], role: str) -> List[Tuple[ParticipantFeatures, float]]:
        scored = [(p, self.score_player_for_role(p, role)) for p in players]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def get_top_n_for_role(self, players: List[ParticipantFeatures], role: str, n: int = 10) -> List[Tuple[ParticipantFeatures, float]]:
        ranked = self.rank_players_for_role(players, role)
        return ranked[:n]
