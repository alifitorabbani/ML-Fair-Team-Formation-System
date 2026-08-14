from typing import Dict, List, Optional, Tuple
from app.optimization.config.role_config import RoleCompatibilityMatrix, OptimizationConfig
from app.schemas.schemas import ParticipantFeatures


class RoleCompatibilityEngine:
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.matrix = config.compatibility_matrix

    def get_compatibility(self, from_role: str, to_role: str) -> float:
        return self.matrix.get_compatibility(from_role, to_role)

    def get_role_scores(self, player: ParticipantFeatures, target_role: str) -> Dict[str, float]:
        scores = {}
        for role in ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]:
            scores[role] = self._calculate_score(player, role)
        return scores

    def _calculate_score(self, player: ParticipantFeatures, target_role: str) -> float:
        if target_role == player.primary_lane:
            return 1.0
        if target_role == player.secondary_lane:
            return 1.0
        return self.get_compatibility(player.primary_lane, target_role)

    def get_best_available_roles(self, player: ParticipantFeatures, available_roles: List[str]) -> List[Tuple[str, float]]:
        scored = [(role, self._calculate_score(player, role)) for role in available_roles]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
