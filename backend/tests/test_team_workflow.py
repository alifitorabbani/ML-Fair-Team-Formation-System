import pytest
from app.optimization.team_optimizer import TeamOptimizer
from app.optimization.config.role_config import OptimizationConfig
from app.schemas.schemas import ParticipantFeatures


def create_test_participant(player_id: str, primary_lane: str, skill_score: float) -> ParticipantFeatures:
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
        primary_lane=primary_lane,
        secondary_lane=None,
        primary_lane_comfort=1,
        secondary_lane_comfort=None,
        skill_score=skill_score,
        role_flexibility_score=100.0,
        jungle_comfort=5.0 if primary_lane == "Jungle" else 0.0,
        exp_comfort=5.0 if primary_lane == "EXP Lane" else 0.0,
        mid_comfort=5.0 if primary_lane == "Mid Lane" else 0.0,
        gold_comfort=5.0 if primary_lane == "Gold Lane" else 0.0,
        roam_comfort=5.0 if primary_lane == "Roam" else 0.0,
        lane_capabilities={
            "Jungle": 5.0 if primary_lane == "Jungle" else 0.0,
            "EXP Lane": 5.0 if primary_lane == "EXP Lane" else 0.0,
            "Mid Lane": 5.0 if primary_lane == "Mid Lane" else 0.0,
            "Gold Lane": 5.0 if primary_lane == "Gold Lane" else 0.0,
            "Roam": 5.0 if primary_lane == "Roam" else 0.0,
        },
    )


class TestTeamGenerationMultipleOf5:
    def test_5_participants_generates_1_team(self):
        participants = [
            create_test_participant(f"P{i:03d}", "Jungle", 80.0)
            for i in range(5)
        ]
        participants[0].primary_lane = "EXP Lane"
        participants[0].lane_capabilities["EXP Lane"] = 5.0
        participants[0].lane_capabilities["Jungle"] = 0.0
        participants[1].primary_lane = "Mid Lane"
        participants[1].lane_capabilities["Mid Lane"] = 5.0
        participants[1].lane_capabilities["Jungle"] = 0.0
        participants[2].primary_lane = "Gold Lane"
        participants[2].lane_capabilities["Gold Lane"] = 5.0
        participants[2].lane_capabilities["Jungle"] = 0.0
        participants[3].primary_lane = "Roam"
        participants[3].lane_capabilities["Roam"] = 5.0
        participants[3].lane_capabilities["Jungle"] = 0.0
        participants[4].primary_lane = "Jungle"

        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        config.fairness_threshold = 0.0
        optimizer = TeamOptimizer(participants, num_teams=1, seed=42, config=config)
        teams, iterations, fairness = optimizer.optimize()
        assert len(teams) == 1
        assert len(teams[0].players) == 5

    def test_10_participants_generates_2_teams(self):
        participants = []
        lanes = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]
        for i in range(10):
            lane = lanes[i % 5]
            p = create_test_participant(f"P{i:03d}", lane, 80.0 - i)
            participants.append(p)

        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        config.fairness_threshold = 0.0
        optimizer = TeamOptimizer(participants, num_teams=2, seed=42, config=config)
        teams, iterations, fairness = optimizer.optimize()
        assert len(teams) == 2
        for team in teams:
            assert len(team.players) == 5

    def test_15_participants_generates_3_teams(self):
        participants = []
        lanes = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]
        for i in range(15):
            lane = lanes[i % 5]
            p = create_test_participant(f"P{i:03d}", lane, 80.0 - i)
            participants.append(p)

        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        config.fairness_threshold = 0.0
        optimizer = TeamOptimizer(participants, num_teams=3, seed=42, config=config)
        teams, iterations, fairness = optimizer.optimize()
        assert len(teams) == 3
        for team in teams:
            assert len(team.players) == 5

    def test_qualification_formula(self):
        for total in [5, 6, 9, 10, 11, 14, 15, 19, 20, 23, 24, 25]:
            qualified = (total // 5) * 5
            eliminated = total - qualified
            assert qualified % 5 == 0
            assert qualified + eliminated == total
