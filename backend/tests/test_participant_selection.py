import pytest
from app.optimization.participant_selector import ParticipantSelector
from app.schemas.schemas import ParticipantFeatures


def create_test_participant(player_id: str, primary_lane: str, skill_score: float, comfort: int) -> ParticipantFeatures:
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
        primary_lane_comfort=comfort,
        secondary_lane_comfort=None,
        skill_score=skill_score,
        role_flexibility_score=80.0,
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


class TestParticipantSelector:
    def test_selects_correct_number(self):
        participants = [
            create_test_participant(f"P{i:03d}", "Jungle", 50.0 + i, 5)
            for i in range(10)
        ]
        selector = ParticipantSelector(participants, num_teams=2)
        selected, not_selected = selector.select_optimal_subset()
        assert len(selected) == 10
        assert len(not_selected) == 0

    def test_excludes_participants_when_over(self):
        participants = [
            create_test_participant(f"P{i:03d}", "Jungle", 50.0 + i, 5)
            for i in range(12)
        ]
        selector = ParticipantSelector(participants, num_teams=2)
        selected, not_selected = selector.select_optimal_subset()
        assert len(selected) == 10
        assert len(not_selected) == 2

    def test_insufficient_participants(self):
        participants = [
            create_test_participant(f"P{i:03d}", "Jungle", 50.0 + i, 5)
            for i in range(4)
        ]
        selector = ParticipantSelector(participants, num_teams=1)
        selected, not_selected = selector.select_optimal_subset()
        assert len(selected) <= 4
