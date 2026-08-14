from typing import Dict, List, Tuple
from app.optimization.config.role_config import RoleDemandConfig
from app.schemas.schemas import ParticipantFeatures


class RoleDemandAnalyzer:
    def __init__(self, participants: List[ParticipantFeatures], config: RoleDemandConfig):
        self.participants = participants
        self.config = config
        self.roles = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]
        self.demand: Dict[str, int] = {r: 0 for r in self.roles}
        self._analyze()

    def _analyze(self) -> None:
        for p in self.participants:
            if p.primary_lane in self.demand:
                self.demand[p.primary_lane] += 1
            if p.secondary_lane and p.secondary_lane in self.demand:
                self.demand[p.secondary_lane] += 1

    def get_shortage_roles(self, total_slots: int) -> List[str]:
        ideal = total_slots * self.config.ideal_percentage
        return [r for r in self.roles if self.demand[r] < ideal * self.config.shortage_threshold]

    def get_surplus_roles(self, total_slots: int) -> List[str]:
        ideal = total_slots * self.config.ideal_percentage
        return [r for r in self.roles if self.demand[r] > ideal * self.config.surplus_threshold]

    def get_role_demand_status(self, total_slots: int) -> Dict[str, str]:
        ideal = total_slots * self.config.ideal_percentage
        status = {}
        for r in self.roles:
            ratio = self.demand[r] / ideal if ideal > 0 else 1.0
            if ratio < self.config.high_shortage_threshold:
                status[r] = "HIGH_SHORTAGE"
            elif ratio < self.config.shortage_threshold:
                status[r] = "SHORTAGE"
            elif ratio > self.config.high_surplus_threshold:
                status[r] = "HIGH_SURPLUS"
            elif ratio > self.config.surplus_threshold:
                status[r] = "SURPLUS"
            else:
                status[r] = "NORMAL"
        return status

    def get_fill_candidates(self, shortage_role: str) -> List[Tuple[ParticipantFeatures, float]]:
        candidates = []
        for p in self.participants:
            if p.primary_lane == shortage_role or p.secondary_lane == shortage_role:
                continue
            candidates.append((p, 1.0))
        return candidates
