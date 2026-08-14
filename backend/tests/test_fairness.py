import pytest
from app.optimization.team_optimizer import TeamOptimizer
from app.optimization.config.role_config import OptimizationConfig
from app.schemas.schemas import ParticipantFeatures


def create_test_participant(player_id: str, skill_score: float, comfort: int) -> ParticipantFeatures:
    return ParticipantFeatures(
        player_id=player_id,
        name=f"Player {player_id}",
        current_rank="Mythic",
        current_stars=25,
        highest_rank="Mythical Honor",
        highest_stars=50,
        current_rank_score=70.0,
        current_star_score=100.0,
        highest_rank_score=80.0,
        highest_star_score=50.0,
        primary_lane="Jungle",
        secondary_lane=None,
        primary_lane_comfort=comfort,
        secondary_lane_comfort=None,
        skill_score=skill_score,
        role_flexibility_score=80.0,
        jungle_comfort=5.0,
        exp_comfort=0.0,
        mid_comfort=0.0,
        gold_comfort=0.0,
        roam_comfort=0.0,
        lane_capabilities={
            "Jungle": 5.0,
            "EXP Lane": 0.0,
            "Mid Lane": 0.0,
            "Gold Lane": 0.0,
            "Roam": 0.0,
        },
    )


class TestFairnessCalculation:
    def test_fairness_score_bounds(self):
        participants = [create_test_participant(f"P{i:03d}", 80.0, 5) for i in range(5)]
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        config.fairness_threshold = 0.0
        optimizer = TeamOptimizer(participants, num_teams=1, seed=42, config=config)
        teams, _, fairness = optimizer.optimize()
        assert 0 <= fairness <= 100

    def test_equal_skill_teams_high_fairness(self):
        lanes = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]
        participants = []
        for i in range(5):
            capabilities = {lane: 0.0 for lane in lanes}
            capabilities[lanes[i]] = 5.0
            capabilities[lanes[(i + 1) % 5]] = 3.0
            participants.append(
                ParticipantFeatures(
                    player_id=f"P{i:03d}",
                    name=f"Player {i:03d}",
                    current_rank="Mythic",
                    current_stars=25,
                    highest_rank="Mythical Honor",
                    highest_stars=50,
                    current_rank_score=70.0,
                    current_star_score=100.0,
                    highest_rank_score=80.0,
                    highest_star_score=50.0,
                    primary_lane=lanes[i],
                    secondary_lane=lanes[(i + 1) % 5],
                    primary_lane_comfort=5,
                    secondary_lane_comfort=3,
                    skill_score=85.0,
                    role_flexibility_score=80.0,
                    jungle_comfort=5.0 if lanes[i] == "Jungle" or lanes[(i + 1) % 5] == "Jungle" else 0.0,
                    exp_comfort=5.0 if lanes[i] == "EXP Lane" or lanes[(i + 1) % 5] == "EXP Lane" else 0.0,
                    mid_comfort=5.0 if lanes[i] == "Mid Lane" or lanes[(i + 1) % 5] == "Mid Lane" else 0.0,
                    gold_comfort=5.0 if lanes[i] == "Gold Lane" or lanes[(i + 1) % 5] == "Gold Lane" else 0.0,
                    roam_comfort=5.0 if lanes[i] == "Roam" or lanes[(i + 1) % 5] == "Roam" else 0.0,
                    lane_capabilities=capabilities,
                )
            )
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        config.fairness_threshold = 0.0
        optimizer = TeamOptimizer(participants, num_teams=1, seed=42, config=config)
        _, iterations, fairness = optimizer.optimize()
        assert fairness > 60
