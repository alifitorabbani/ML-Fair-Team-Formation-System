from pydantic import BaseModel
from typing import Dict, List, Optional


class RoleCompatibilityMatrix(BaseModel):
    matrix: Dict[str, Dict[str, float]]

    @classmethod
    def get_default(cls) -> "RoleCompatibilityMatrix":
        return cls(
            matrix={
                "Jungle": {
                    "Jungle": 1.0,
                    "EXP Lane": 0.7,
                    "Mid Lane": 0.8,
                    "Gold Lane": 0.6,
                    "Roam": 0.7,
                },
                "EXP Lane": {
                    "Jungle": 0.5,
                    "EXP Lane": 1.0,
                    "Mid Lane": 0.6,
                    "Gold Lane": 0.5,
                    "Roam": 0.9,
                },
                "Mid Lane": {
                    "Jungle": 0.8,
                    "EXP Lane": 0.6,
                    "Mid Lane": 1.0,
                    "Gold Lane": 0.6,
                    "Roam": 0.9,
                },
                "Gold Lane": {
                    "Jungle": 0.5,
                    "EXP Lane": 0.4,
                    "Mid Lane": 0.6,
                    "Gold Lane": 1.0,
                    "Roam": 0.3,
                },
                "Roam": {
                    "Jungle": 0.3,
                    "EXP Lane": 0.5,
                    "Mid Lane": 0.7,
                    "Gold Lane": 0.2,
                    "Roam": 1.0,
                },
            }
        )

    def get_compatibility(self, from_role: str, to_role: str) -> float:
        if from_role not in self.matrix:
            return 0.5
        return self.matrix[from_role].get(to_role, 0.5)

    def update_compatibility(self, from_role: str, to_role: str, value: float) -> None:
        if from_role not in self.matrix:
            self.matrix[from_role] = {r: 0.5 for r in ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]}
        self.matrix[from_role][to_role] = max(0.0, min(1.0, value))


class ScoringWeights(BaseModel):
    role_compatibility: float = 0.0
    role_preference: float = 0.0
    skill_balance: float = 0.6
    role_distribution: float = 0.4

    @classmethod
    def get_default(cls) -> "ScoringWeights":
        return cls()


class RoleDemandConfig(BaseModel):
    ideal_percentage: float = 0.20
    shortage_threshold: float = 0.80
    surplus_threshold: float = 1.20
    high_shortage_threshold: float = 0.50
    high_surplus_threshold: float = 1.50

    @classmethod
    def get_default(cls) -> "RoleDemandConfig":
        return cls()


class OptimizationConfig(BaseModel):
    compatibility_matrix: RoleCompatibilityMatrix = RoleCompatibilityMatrix.get_default()
    scoring_weights: ScoringWeights = ScoringWeights.get_default()
    role_demand: RoleDemandConfig = RoleDemandConfig.get_default()
    top_n_candidates: int = 8
    max_iterations: int = 500
    fairness_threshold: float = 80.0
    repeated_pairing_penalty: float = 5.0
    role_history_penalty: float = 3.0
    enable_history: bool = True
    team_size: int = 5

    @classmethod
    def get_default(cls) -> "OptimizationConfig":
        return cls()
