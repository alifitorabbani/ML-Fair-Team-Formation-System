from typing import Dict, List, Tuple
import numpy as np
from app.optimization.config.role_config import OptimizationConfig
from app.optimization.engines.role_compatibility_engine import RoleCompatibilityEngine
from app.schemas.schemas import ParticipantFeatures


class TeamFairnessEvaluator:
    def __init__(self, config: OptimizationConfig, engine: RoleCompatibilityEngine):
        self.config = config
        self.engine = engine

    def evaluate_team(self, team: List[Tuple[ParticipantFeatures, str]]) -> Dict[str, float]:
        if not team:
            return {
                "role_compatibility": 0.0,
                "role_preference": 0.0,
                "skill_balance": 0.0,
                "role_distribution": 0.0,
                "overall": 0.0,
            }

        skill_scores = []
        roles_assigned = set()

        for player, assigned_role in team:
            skill_scores.append(player.skill_score)
            roles_assigned.add(assigned_role)

        skill_balance = max(0.0, 100.0 - float(np.std(skill_scores)) * 5.0)
        role_dist = (len(roles_assigned) / 5.0) * 100.0

        overall = (
            self.config.scoring_weights.skill_balance * skill_balance +
            self.config.scoring_weights.role_distribution * role_dist
        )

        return {
            "role_compatibility": 0.0,
            "role_preference": 0.0,
            "skill_balance": round(skill_balance, 2),
            "role_distribution": round(role_dist, 2),
            "overall": round(overall, 2),
        }


