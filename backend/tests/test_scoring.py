import pytest
from app.config.constants import Rank, RANK_SCORES, MAX_STARS_PER_RANK, RANK_ALIASES
from app.preprocessing.features import (
    normalize_star_score,
    calculate_skill_score,
    calculate_role_flexibility_score,
    calculate_lane_comforts,
)


class TestRankNormalization:
    def test_mythic_normalization(self):
        from app.preprocessing.validation import normalize_rank
        assert normalize_rank("Mythic") == Rank.mythic

    def test_alias_normalization(self):
        from app.preprocessing.validation import normalize_rank
        assert normalize_rank("grand master") == Rank.grandmaster

    def test_invalid_rank(self):
        from app.preprocessing.validation import normalize_rank
        assert normalize_rank("InvalidRank") is None


class TestStarNormalization:
    def test_mythic_star_normalization(self):
        result = normalize_star_score(Rank.mythic, 25)
        assert result == 100.0

    def test_epic_star_normalization(self):
        result = normalize_star_score(Rank.epic, 5)
        assert result == 50.0

    def test_zero_stars(self):
        result = normalize_star_score(Rank.epic, 0)
        assert result == 0.0


class TestSkillScore:
    def test_skill_score_calculation(self):
        score = calculate_skill_score(70.0, 50.0, 90.0, 80.0)
        expected = 0.40 * 70 + 0.20 * 50 + 0.25 * 90 + 0.15 * 80
        assert abs(score - expected) < 0.01

    def test_skill_score_bounds(self):
        score = calculate_skill_score(100.0, 100.0, 100.0, 100.0)
        assert 0 <= score <= 100


class TestRoleFlexibility:
    def test_high_flexibility(self):
        score = calculate_role_flexibility_score(1, 1)
        assert score == 100.0

    def test_low_flexibility(self):
        score = calculate_role_flexibility_score(1, 5)
        assert score < 100.0

    def test_no_secondary(self):
        score = calculate_role_flexibility_score(1, None)
        assert score == 100.0


class TestLaneComforts:
    def test_primary_lane_comfort(self):
        comforts = calculate_lane_comforts("Jungle", "Mid Lane", 1, 2)
        assert comforts["Jungle"] == 5.0
        assert comforts["Mid Lane"] == 4.0

    def test_zero_for_unknown_lanes(self):
        comforts = calculate_lane_comforts("Jungle", None, 1, None)
        assert comforts["EXP Lane"] == 0.0
        assert comforts["Gold Lane"] == 0.0
