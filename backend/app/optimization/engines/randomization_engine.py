from typing import Dict, List, Tuple, Optional
import random
import numpy as np
from app.optimization.config.role_config import OptimizationConfig
from app.optimization.engines.role_compatibility_engine import RoleCompatibilityEngine
from app.optimization.scoring.team_fairness_evaluator import TeamFairnessEvaluator
from app.optimization.scoring.player_role_scorer import PlayerRoleScorer
from app.schemas.schemas import ParticipantFeatures


class RandomizationEngine:
    def __init__(self, config: OptimizationConfig, engine: RoleCompatibilityEngine, scorer: PlayerRoleScorer, evaluator: TeamFairnessEvaluator, seed: int):
        self.config = config
        self.engine = engine
        self.scorer = scorer
        self.evaluator = evaluator
        self.rng = random.Random(seed)

    def select_weighted_random(self, candidates: List[Tuple[ParticipantFeatures, float]]) -> Optional[ParticipantFeatures]:
        if not candidates:
            return None
        weights = [max(0.01, score) for _, score in candidates]
        total = sum(weights)
        if total == 0:
            return self.rng.choice([p for p, _ in candidates])
        pick = self.rng.uniform(0, total)
        current = 0.0
        for (player, score) in candidates:
            current += max(0.01, score)
            if pick <= current:
                return player
        return candidates[-1][0]

    def select_top_n_weighted(self, candidates: List[Tuple[ParticipantFeatures, float]], n: int) -> List[ParticipantFeatures]:
        if len(candidates) <= n:
            return [p for p, _ in candidates]
        sorted_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)
        top_candidates = sorted_candidates[:n]
        selected = self.select_weighted_random(top_candidates)
        return [selected] if selected else []

    def _team_avg_skill(self, team: List[Tuple[ParticipantFeatures, str]]) -> float:
        if not team:
            return 0.0
        return sum(p.skill_score for p, _ in team) / len(team)

    def _global_avg_skill(self, participants: List[ParticipantFeatures]) -> float:
        if not participants:
            return 0.0
        return sum(p.skill_score for p in participants) / len(participants)

    def _choose_best_team_for_primary(
        self,
        player: ParticipantFeatures,
        eligible: List[int],
        teams: List[List[Tuple[ParticipantFeatures, str]]],
        participants: List[ParticipantFeatures],
    ) -> int:
        global_avg = self._global_avg_skill(participants)
        def team_cost(ti: int) -> Tuple[float, int, float]:
            avg = self._team_avg_skill(teams[ti])
            return (avg - global_avg, len(teams[ti]), self.rng.random())
        return min(eligible, key=team_cost)

    def _choose_best_team_for_remaining(
        self,
        player: ParticipantFeatures,
        teams: List[List[Tuple[ParticipantFeatures, str]]],
        participants: List[ParticipantFeatures],
    ) -> Optional[int]:
        global_avg = self._global_avg_skill(participants)
        best_team = None
        best_score = float("inf")
        for ti in range(len(teams)):
            if len(teams[ti]) >= self.config.team_size:
                continue
            avg = self._team_avg_skill(teams[ti])
            score = abs(avg - global_avg) + len(teams[ti]) * 0.1 + self.rng.random() * 0.5
            if score < best_score:
                best_score = score
                best_team = ti
        return best_team

    def _choose_best_role_for_player(self, player: ParticipantFeatures, available: List[str]) -> str:
        role_scores = self.engine.get_best_available_roles(player, available)
        if role_scores:
            return role_scores[0][0]
        return available[0]

    def generate_candidates(self, participants: List[ParticipantFeatures], num_teams: int, shortage_roles: List[str]) -> List[List[List[Tuple[ParticipantFeatures, str]]]]:
        candidates: List[Tuple[List[List[Tuple[ParticipantFeatures, str]]], float]] = []
        for _ in range(self.config.max_iterations):
            team_assignments = self._generate_single_candidate(participants, num_teams, shortage_roles)
            if team_assignments and all(len(t) == self.config.team_size for t in team_assignments):
                fairness_values = [self.evaluator.evaluate_team(t)["overall"] for t in team_assignments if t]
                if not fairness_values:
                    continue
                min_fairness = min(fairness_values)
                fairness_gap = max(fairness_values) - min_fairness
                # Prefer candidates with higher min fairness AND lower fairness gap between teams
                score = min_fairness - fairness_gap * 0.5
                candidates.append((team_assignments, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [team for team, _ in candidates[:self.config.top_n_candidates]]

    def _generate_single_candidate(self, participants: List[ParticipantFeatures], num_teams: int, shortage_roles: List[str]) -> List[List[Tuple[ParticipantFeatures, str]]]:
        all_roles = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]
        
        players = participants[:]
        self.rng.shuffle(players)
        
        teams: List[List[Tuple[ParticipantFeatures, str]]] = [[] for _ in range(num_teams)]
        lane_count_per_team = [{role: 0 for role in all_roles} for _ in range(num_teams)]
        assigned = set()
        
        # ========================================================================
        # PHASE 1: Ensure every team has at least 1 player per lane (coverage)
        # Process roles by scarcity to avoid running out of players for rare roles
        # ========================================================================
        role_player_counts = []
        for role in all_roles:
            role_players = [p for p in players if p.primary_lane == role or p.secondary_lane == role]
            role_player_counts.append((role, len(role_players)))
        role_player_counts.sort(key=lambda x: x[1])
        
        for role, _ in role_player_counts:
            role_players = [p for p in players if p.primary_lane == role or p.secondary_lane == role]
            role_players.sort(key=lambda p: -p.skill_score)
            
            for player in role_players:
                if player.player_id in assigned:
                    continue
                if len([t for t in teams if len(t) == self.config.team_size]) >= num_teams:
                    break
                
                eligible = [ti for ti in range(num_teams) 
                           if len(teams[ti]) < self.config.team_size 
                           and lane_count_per_team[ti][role] == 0]
                if not eligible:
                    continue
                
                best_team = self._choose_best_team_for_primary(player, eligible, teams, participants)
                teams[best_team].append((player, role))
                lane_count_per_team[best_team][role] += 1
                assigned.add(player.player_id)
        
        # ========================================================================
        # PHASE 2: Assign remaining players with skill balance + lane preference
        # ========================================================================
        unassigned = [p for p in players if p.player_id not in assigned]
        
        for player in unassigned:
            if len([t for t in teams if len(t) == self.config.team_size]) >= num_teams:
                break
            
            role_preferences = []
            preferred = []
            if player.primary_lane in all_roles:
                preferred.append(player.primary_lane)
            if player.secondary_lane and player.secondary_lane in all_roles and player.secondary_lane != player.primary_lane:
                preferred.append(player.secondary_lane)
            
            for role in preferred:
                role_preferences.append((role, 1.0))
            for role in all_roles:
                if role not in preferred:
                    role_preferences.append((role, 2.0))
            
            role_preferences.sort(key=lambda x: x[1])
            
            best_team = None
            best_role = None
            best_score = float("inf")
            
            for role, _ in role_preferences:
                for ti in range(num_teams):
                    if len(teams[ti]) >= self.config.team_size:
                        continue
                    
                    team_skills = [ps.skill_score for ps, _ in teams[ti]]
                    if team_skills:
                        team_avg = sum(team_skills) / len(team_skills)
                        global_avg = self._global_avg_skill(participants)
                        skill_penalty = max(0.0, team_avg - global_avg) * 2.0
                    else:
                        skill_penalty = 0.0
                    
                    score = skill_penalty
                    
                    if score < best_score:
                        best_score = score
                        best_team = ti
                        best_role = role
            
            if best_team is not None and best_role is not None:
                teams[best_team].append((player, best_role))
                lane_count_per_team[best_team][best_role] += 1
                assigned.add(player.player_id)
        
        # ========================================================================
        # VALIDATION: All teams must have exactly team_size players
        # ========================================================================
        for ti in range(num_teams):
            if len(teams[ti]) != self.config.team_size:
                return []
        
        return teams

    def pick_final_team(self, candidates: List[List[List[Tuple[ParticipantFeatures, str]]]]) -> List[List[Tuple[ParticipantFeatures, str]]]:
        if not candidates:
            return []
        top_n = candidates[:self.config.top_n_candidates]
        fairness_scores = []
        for team_set in top_n:
            fairness_values = [self.evaluator.evaluate_team(t)["overall"] for t in team_set if t]
            if not fairness_values:
                fairness_scores.append(0.0)
            else:
                min_fairness = min(fairness_values)
                fairness_gap = max(fairness_values) - min(fairness_values)
                fairness_scores.append(max(0.1, min_fairness - fairness_gap * 1.0))
        total = sum(fairness_scores)
        if total <= 0:
            return top_n[0]
        pick = self.rng.uniform(0, total)
        current = 0.0
        for i, team_set in enumerate(top_n):
            current += fairness_scores[i]
            if pick <= current:
                return team_set
        return top_n[0]
