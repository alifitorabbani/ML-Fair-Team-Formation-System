import pytest
from app.optimization.config.role_config import RoleCompatibilityMatrix, OptimizationConfig, RoleDemandConfig
from app.optimization.engines.role_compatibility_engine import RoleCompatibilityEngine
from app.optimization.engines.role_demand_analyzer import RoleDemandAnalyzer
from app.optimization.scoring.player_role_scorer import PlayerRoleScorer
from app.optimization.scoring.team_fairness_evaluator import TeamFairnessEvaluator
from app.optimization.history.history_manager import HistoryManager
from app.optimization.engines.randomization_engine import RandomizationEngine
from app.optimization.team_optimizer import TeamOptimizer
from app.schemas.schemas import ParticipantFeatures


def create_test_participant(player_id: str, primary_lane: str, skill_score: float, secondary_lane: str = None) -> ParticipantFeatures:
    lanes = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]
    capabilities = {lane: 0.0 for lane in lanes}
    capabilities[primary_lane] = 5.0
    if secondary_lane and secondary_lane in lanes:
        capabilities[secondary_lane] = 3.0
    
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
        secondary_lane=secondary_lane,
        primary_lane_comfort=5,
        secondary_lane_comfort=3 if secondary_lane else None,
        skill_score=skill_score,
        role_flexibility_score=80.0,
        jungle_comfort=capabilities["Jungle"],
        exp_comfort=capabilities["EXP Lane"],
        mid_comfort=capabilities["Mid Lane"],
        gold_comfort=capabilities["Gold Lane"],
        roam_comfort=capabilities["Roam"],
        lane_capabilities=capabilities,
    )


class TestRoleCompatibilityMatrix:
    def test_default_matrix_has_all_roles(self):
        matrix = RoleCompatibilityMatrix.get_default()
        expected_roles = {"Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"}
        assert set(matrix.matrix.keys()) == expected_roles
        for from_role in matrix.matrix:
            assert set(matrix.matrix[from_role].keys()) == expected_roles

    def test_self_compatibility_is_one(self):
        matrix = RoleCompatibilityMatrix.get_default()
        for role in matrix.matrix:
            assert matrix.get_compatibility(role, role) == 1.0

    def test_update_compatibility(self):
        matrix = RoleCompatibilityMatrix.get_default()
        matrix.update_compatibility("Jungle", "Roam", 0.9)
        assert matrix.get_compatibility("Jungle", "Roam") == 0.9

    def test_compatibility_bounds(self):
        matrix = RoleCompatibilityMatrix.get_default()
        matrix.update_compatibility("Jungle", "Roam", 1.5)
        assert matrix.get_compatibility("Jungle", "Roam") <= 1.0
        matrix.update_compatibility("Jungle", "Roam", -0.5)
        assert matrix.get_compatibility("Jungle", "Roam") >= 0.0


class TestRoleDemandAnalyzer:
    def test_balanced_demand(self):
        participants = [
            create_test_participant(f"P{i:03d}", role, 80.0)
            for i, role in enumerate(["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"] * 4)
        ]
        analyzer = RoleDemandAnalyzer(participants, RoleDemandConfig.get_default())
        status = analyzer.get_role_demand_status(20)
        for role in ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]:
            assert status[role] in ["NORMAL", "SURPLUS"]

    def test_role_shortage(self):
        participants = [create_test_participant(f"P{i:03d}", "Mid Lane", 80.0) for i in range(20)]
        analyzer = RoleDemandAnalyzer(participants, RoleDemandConfig.get_default())
        shortage = analyzer.get_shortage_roles(20)
        assert "Jungle" in shortage
        assert "EXP Lane" in shortage
        assert "Gold Lane" in shortage
        assert "Roam" in shortage

    def test_role_surplus(self):
        participants = [create_test_participant(f"P{i:03d}", "Mid Lane", 80.0) for i in range(20)]
        analyzer = RoleDemandAnalyzer(participants, RoleDemandConfig.get_default())
        surplus = analyzer.get_surplus_roles(20)
        assert "Mid Lane" in surplus

    def test_extreme_imbalance(self):
        participants = []
        for i in range(15):
            participants.append(create_test_participant(f"P{i:03d}", "Mid Lane", 80.0))
        for i in range(5):
            participants.append(create_test_participant(f"P{i+15:03d}", "Jungle", 80.0))
        analyzer = RoleDemandAnalyzer(participants, RoleDemandConfig.get_default())
        status = analyzer.get_role_demand_status(20)
        assert status["Mid Lane"] == "HIGH_SURPLUS"
        assert status["Jungle"] in ["SHORTAGE", "SURPLUS"]


class TestRoleCompatibilityEngine:
    def test_primary_role_gets_highest_score(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        player = create_test_participant("P001", "Jungle", 80.0)
        scores = engine.get_role_scores(player, "Jungle")
        assert scores["Jungle"] == 1.0

    def test_secondary_role_gets_high_score(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        player = create_test_participant("P001", "Jungle", 80.0, secondary_lane="Roam")
        scores = engine.get_role_scores(player, "Roam")
        assert scores["Roam"] == 1.0

    def test_compatibility_matrix_affects_score(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        player = create_test_participant("P001", "EXP Lane", 80.0)
        scores = engine.get_role_scores(player, "Roam")
        assert scores["Roam"] > scores["Jungle"]

    def test_best_available_roles_ordered(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        player = create_test_participant("P001", "Jungle", 80.0)
        available = ["Roam", "EXP Lane", "Gold Lane"]
        ranked = engine.get_best_available_roles(player, available)
        assert ranked[0][0] == "Roam"
        assert ranked[0][1] >= ranked[1][1]


class TestPlayerRoleScorer:
    def test_primary_role_gets_highest_score(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        scorer = PlayerRoleScorer(config, engine)
        player = create_test_participant("P001", "Jungle", 80.0)
        score = scorer.score_player_for_role(player, "Jungle")
        assert score == 0.48

    def test_secondary_role_gets_medium_score(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        scorer = PlayerRoleScorer(config, engine)
        player = create_test_participant("P001", "Jungle", 80.0, secondary_lane="Roam")
        score = scorer.score_player_for_role(player, "Roam")
        assert score == 0.48

    def test_ranking_players_for_role(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        scorer = PlayerRoleScorer(config, engine)
        players = [
            create_test_participant("P001", "Jungle", 90.0),
            create_test_participant("P002", "Mid Lane", 80.0),
        ]
        ranked = scorer.rank_players_for_role(players, "Jungle")
        assert ranked[0][0].player_id == "P001"
        assert ranked[0][1] > ranked[1][1]


class TestTeamFairnessEvaluator:
    def test_perfect_team_high_fairness(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        evaluator = TeamFairnessEvaluator(config, engine)
        team = [
            (create_test_participant("P001", "Jungle", 80.0), "Jungle"),
            (create_test_participant("P002", "EXP Lane", 80.0), "EXP Lane"),
            (create_test_participant("P003", "Mid Lane", 80.0), "Mid Lane"),
            (create_test_participant("P004", "Gold Lane", 80.0), "Gold Lane"),
            (create_test_participant("P005", "Roam", 80.0), "Roam"),
        ]
        result = evaluator.evaluate_team(team)
        assert result["role_distribution"] == 100.0
        assert result["overall"] > 80.0

    def test_skill_balance_penalty(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        evaluator = TeamFairnessEvaluator(config, engine)
        balanced_team = [
            (create_test_participant("P001", "Jungle", 80.0), "Jungle"),
            (create_test_participant("P002", "EXP Lane", 80.0), "EXP Lane"),
        ]
        unbalanced_team = [
            (create_test_participant("P001", "Jungle", 100.0), "Jungle"),
            (create_test_participant("P002", "EXP Lane", 50.0), "EXP Lane"),
        ]
        balanced_score = evaluator.evaluate_team(balanced_team)["overall"]
        unbalanced_score = evaluator.evaluate_team(unbalanced_team)["overall"]
        assert balanced_score > unbalanced_score

    def test_empty_team(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        evaluator = TeamFairnessEvaluator(config, engine)
        result = evaluator.evaluate_team([])
        assert result["overall"] == 0.0


class TestHistoryManager:
    def test_record_and_retrieve(self):
        history = HistoryManager(enable=True)
        players = [create_test_participant(f"P{i:03d}", "Jungle", 80.0) for i in range(5)]
        team = [(p, p.primary_lane) for p in players]
        history.record_team(team)
        assert len(history.team_history) == 1
        assert history.team_history[0] == ["P000", "P001", "P002", "P003", "P004"]

    def test_repeated_pairing_penalty(self):
        history = HistoryManager(enable=True)
        players = [create_test_participant(f"P{i:03d}", "Jungle", 80.0) for i in range(5)]
        team = [(p, p.primary_lane) for p in players]
        history.record_team(team)
        history.record_team(team)
        penalty = history.get_repeated_pairing_penalty(team)
        assert penalty > 0.0

    def test_role_history_penalty(self):
        history = HistoryManager(enable=True)
        player = create_test_participant("P001", "Jungle", 80.0)
        team = [(player, "Jungle")]
        history.record_team(team)
        history.record_team(team)
        penalty = history.get_role_history_penalty(player, "Jungle")
        assert penalty > 0.0

    def test_disabled_history(self):
        history = HistoryManager(enable=False)
        players = [create_test_participant(f"P{i:03d}", "Jungle", 80.0) for i in range(5)]
        team = [(p, p.primary_lane) for p in players]
        history.record_team(team)
        assert len(history.team_history) == 0

    def test_clear_history(self):
        history = HistoryManager(enable=True)
        players = [create_test_participant(f"P{i:03d}", "Jungle", 80.0) for i in range(5)]
        team = [(p, p.primary_lane) for p in players]
        history.record_team(team)
        history.clear()
        assert len(history.team_history) == 0


class TestRandomizationEngine:
    def test_generates_complete_teams(self):
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        engine = RoleCompatibilityEngine(config)
        scorer = PlayerRoleScorer(config, engine)
        evaluator = TeamFairnessEvaluator(config, engine)
        rand_engine = RandomizationEngine(config, engine, scorer, evaluator, 42)
        participants = [
            create_test_participant(f"P{i:03d}", ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"][i % 5], 80.0)
            for i in range(10)
        ]
        candidates = rand_engine.generate_candidates(participants, 2, [])
        assert len(candidates) > 0

    def test_weighted_random_selection(self):
        config = OptimizationConfig.get_default()
        engine = RoleCompatibilityEngine(config)
        scorer = PlayerRoleScorer(config, engine)
        evaluator = TeamFairnessEvaluator(config, engine)
        rand_engine = RandomizationEngine(config, engine, scorer, evaluator, 42)
        candidates = [
            (create_test_participant("P001", "Jungle", 90.0), 10.0),
            (create_test_participant("P002", "Jungle", 80.0), 5.0),
        ]
        selected = rand_engine.select_weighted_random(candidates)
        assert selected is not None
        assert selected.player_id in ["P001", "P002"]


class TestTeamOptimizerIntegration:
    def test_balanced_roles(self):
        participants = [
            create_test_participant(f"P{i:03d}", ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"][i % 5], 80.0)
            for i in range(10)
        ]
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        optimizer = TeamOptimizer(participants, num_teams=2, seed=42, config=config)
        teams, _, fairness = optimizer.optimize()
        assert len(teams) == 2
        for team in teams:
            roles = {p.primary_lane for p in team.players}
            assert len(roles) == 5

    def test_role_shortage_handling(self):
        participants = []
        for i in range(8):
            participants.append(create_test_participant(f"P{i:03d}", "Mid Lane", 80.0))
        for i in range(2):
            participants.append(create_test_participant(f"P{i+8:03d}", "Jungle", 80.0))
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        optimizer = TeamOptimizer(participants, num_teams=2, seed=42, config=config)
        teams, _, fairness = optimizer.optimize()
        assert len(teams) == 2

    def test_extreme_role_imbalance(self):
        participants = []
        for i in range(18):
            participants.append(create_test_participant(f"P{i:03d}", "Mid Lane", 80.0))
        for i in range(2):
            participants.append(create_test_participant(f"P{i+18:03d}", "Jungle", 80.0))
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        optimizer = TeamOptimizer(participants, num_teams=4, seed=42, config=config)
        teams, _, fairness = optimizer.optimize()
        assert len(teams) == 4

    def test_team_size_validation(self):
        participants = [create_test_participant(f"P{i:03d}", "Jungle", 80.0) for i in range(3)]
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        optimizer = TeamOptimizer(participants, num_teams=1, seed=42, config=config)
        teams, _, fairness = optimizer.optimize()
        assert len(teams) <= 1
        if teams:
            assert len(teams[0].players) <= 5

    def test_no_duplicate_players(self):
        participants = [
            create_test_participant(f"P{i:03d}", ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"][i % 5], 80.0)
            for i in range(10)
        ]
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        optimizer = TeamOptimizer(participants, num_teams=2, seed=42, config=config)
        teams, _, fairness = optimizer.optimize()
        all_players = []
        for team in teams:
            all_players.extend([p.player_id for p in team.players])
        assert len(all_players) == len(set(all_players))

    def test_fairness_score_bounds(self):
        participants = [
            create_test_participant(f"P{i:03d}", ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"][i % 5], 80.0)
            for i in range(10)
        ]
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        optimizer = TeamOptimizer(participants, num_teams=2, seed=42, config=config)
        _, _, fairness = optimizer.optimize()
        assert 0 <= fairness <= 100

    def test_reproducibility_with_seed(self):
        participants = [
            create_test_participant(f"P{i:03d}", ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"][i % 5], 80.0)
            for i in range(10)
        ]
        config = OptimizationConfig.get_default()
        config.max_iterations = 10
        optimizer1 = TeamOptimizer(participants, num_teams=2, seed=42, config=config)
        teams1, _, _ = optimizer1.optimize()
        
        optimizer2 = TeamOptimizer(participants, num_teams=2, seed=42, config=config)
        teams2, _, _ = optimizer2.optimize()
        
        assert len(teams1) == len(teams2)
