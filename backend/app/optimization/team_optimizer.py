import numpy as np
import random
from itertools import permutations
from typing import List, Tuple, Optional
from app.schemas.schemas import ParticipantFeatures, TeamPlayer, TeamResult
from app.optimization.config.role_config import OptimizationConfig
from app.optimization.engines.role_compatibility_engine import RoleCompatibilityEngine
from app.optimization.engines.role_demand_analyzer import RoleDemandAnalyzer
from app.optimization.engines.randomization_engine import RandomizationEngine
from app.optimization.scoring.player_role_scorer import PlayerRoleScorer
from app.optimization.scoring.team_fairness_evaluator import TeamFairnessEvaluator
from app.optimization.history.history_manager import HistoryManager


LANES = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]

TEAM_NAMES = [
    "Alucard",
    "Beatrix",
    "Cecilion",
    "Dyrroth",
    "Edith",
    "Floryn",
    "Granger",
    "Hylos",
    "Irithel",
]


class TeamOptimizer:
    def __init__(
        self,
        participants: List[ParticipantFeatures],
        num_teams: int,
        seed: int,
        config: Optional[OptimizationConfig] = None,
        history: Optional[HistoryManager] = None,
    ):
        self.participants = participants
        self.num_teams = num_teams
        self.seed = seed
        self.config = config or OptimizationConfig.get_default()
        self.rng = random.Random(seed)
        self.engine = RoleCompatibilityEngine(self.config)
        self.analyzer = RoleDemandAnalyzer(participants, self.config.role_demand)
        self.scorer = PlayerRoleScorer(self.config, self.engine)
        self.evaluator = TeamFairnessEvaluator(self.config, self.engine)
        self.history = history or HistoryManager(self.config.enable_history)
        self.rand_engine = RandomizationEngine(self.config, self.engine, self.scorer, self.evaluator, seed)

    def _get_rank_score(self, player: ParticipantFeatures) -> float:
        rank_order = {
            "Warrior": 1, "Elite": 2, "Master": 3, "Grandmaster": 4,
            "Epic": 5, "Legend": 6, "Mythic": 7,
            "Mythical Honor": 8, "Mythical Glory": 9, "Mythical Immortal": 10,
        }
        current = rank_order.get(player.current_rank, 0)
        highest = rank_order.get(player.highest_rank, 0)
        return float((current + highest) / 2.0)

    def _get_skill_std(self, teams: List[List[ParticipantFeatures]]) -> float:
        avgs = [np.mean([p.skill_score for p in t]) for t in teams if t]
        return float(np.std(avgs)) if avgs else 0.0

    def _get_rank_std(self, teams: List[List[ParticipantFeatures]]) -> float:
        avgs = [np.mean([self._get_rank_score(p) for p in t]) for t in teams if t]
        return float(np.std(avgs)) if avgs else 0.0

    def _count_roles(self, team: List[ParticipantFeatures]) -> int:
        roles = set()
        for p in team:
            if p.primary_lane in LANES:
                roles.add(p.primary_lane)
            if p.secondary_lane and p.secondary_lane in LANES and p.secondary_lane != p.primary_lane:
                roles.add(p.secondary_lane)
        return len(roles)

    def _role_completeness_score(self, teams: List[List[ParticipantFeatures]]) -> float:
        if not teams:
            return 0.0
        scores = []
        for team in teams:
            count = self._count_roles(team)
            scores.append(count / len(LANES) * 100.0)
        return float(np.mean(scores))

    def _local_search_multi_objective(self, teams: List[List[ParticipantFeatures]]) -> List[List[ParticipantFeatures]]:
        best = [list(t) for t in teams]
        best_role_score = self._role_completeness_score(best)
        best_rank_std = self._get_rank_std(best)
        best_skill_std = self._get_skill_std(best)

        for _ in range(100):
            improved = False
            for i in range(len(best)):
                for j in range(i + 1, len(best)):
                    if len(best[i]) != len(best[j]):
                        continue
                    for pi in range(len(best[i])):
                        for pj in range(len(best[j])):
                            p1 = best[i][pi]
                            p2 = best[j][pj]
                            candidate = [list(t) for t in best]
                            candidate[i][pi], candidate[j][pj] = candidate[j][pj], candidate[i][pi]
                            new_role_score = self._role_completeness_score(candidate)
                            new_rank_std = self._get_rank_std(candidate)
                            new_skill_std = self._get_skill_std(candidate)
                            if new_role_score > best_role_score:
                                best = candidate
                                best_role_score = new_role_score
                                best_rank_std = new_rank_std
                                best_skill_std = new_skill_std
                                improved = True
                                break
                            elif new_role_score == best_role_score:
                                if new_rank_std < best_rank_std:
                                    best = candidate
                                    best_role_score = new_role_score
                                    best_rank_std = new_rank_std
                                    best_skill_std = new_skill_std
                                    improved = True
                                    break
                                elif new_rank_std == best_rank_std and new_skill_std < best_skill_std:
                                    best = candidate
                                    best_role_score = new_role_score
                                    best_rank_std = new_rank_std
                                    best_skill_std = new_skill_std
                                    improved = True
                                    break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
            if not improved:
                break
        return best

    def _score_teams_multi_objective(self, teams: List[List[Tuple[ParticipantFeatures, str]]]) -> Tuple[float, float, List[TeamResult], float]:
        team_results: List[TeamResult] = []
        fairness_scores: List[float] = []
        for i, team in enumerate(teams):
            if not team:
                continue
            players: List[TeamPlayer] = []
            skill_scores: List[float] = []
            assigned_lanes: List[str] = []
            for player, lane in team:
                if lane == player.primary_lane or lane == player.secondary_lane:
                    reason = f"Role sesuai dengan lane {'utama' if lane == player.primary_lane else 'sekunder'} ({lane})"
                    compat_score = 1.0
                else:
                    compat = self.engine.get_compatibility(player.primary_lane, lane)
                    reason = f"Diassign ke {lane} untuk melengkapi 5 lane (compatibility: {compat:.2f}, skill: {player.skill_score:.1f})"
                    compat_score = compat
                
                players.append(
                    TeamPlayer(
                        player_id=player.player_id,
                        name=player.name,
                        full_name=player.full_name,
                        email=player.email,
                        username=player.username,
                        assigned_lane=lane,
                        current_rank=player.current_rank,
                        current_stars=player.current_stars,
                        highest_rank=player.highest_rank,
                        highest_stars=player.highest_stars,
                        primary_lane=player.primary_lane,
                        secondary_lane=player.secondary_lane,
                        primary_lane_comfort=player.primary_lane_comfort,
                        secondary_lane_comfort=player.secondary_lane_comfort,
                        comfort_in_assigned_lane=0,
                        skill_score=player.skill_score,
                        assignment_reason=reason,
                        role_compatibility_score=compat_score,
                    )
                )
                skill_scores.append(player.skill_score)
                assigned_lanes.append(lane)
            avg_skill = float(np.mean(skill_scores))
            global_avg = float(np.mean([p.skill_score for p in self.participants])) if self.participants else 0.0
            skill_deviation = abs(avg_skill - global_avg)
            skill_balance = float(max(0.0, 100.0 - skill_deviation * 3.0))
            skill_std = float(np.std(skill_scores)) if skill_scores else 0.0
            lanes_covered = sum(1 for lane in LANES if lane in assigned_lanes)
            coverage_ratio = lanes_covered / len(LANES)
            role_balance = float(coverage_ratio * 100.0)
            
            rank_scores = [self._get_rank_score(p) for p, _ in team]
            rank_std = float(np.std(rank_scores)) if rank_scores else 0.0
            rank_balance = float(max(0.0, 100.0 - rank_std * 5.0))
            
            fairness = max(0.0, (
                role_balance * 0.40
                + rank_balance * 0.20
                + skill_balance * 0.40
            ))
            team_results.append(
                TeamResult(
                    team_id=TEAM_NAMES[i] if i < len(TEAM_NAMES) else f"Team {chr(65 + i)}",
                    players=players,
                    average_skill_score=round(avg_skill, 2),
                    role_balance_score=round(role_balance, 2),
                    comfort_score=0.0,
                    overall_fairness=round(fairness, 2),
                    fairness_breakdown={
                        "role_balance": round(role_balance, 2),
                        "role_balance_weight": 0.40,
                        "role_balance_contribution": round(role_balance * 0.40, 2),
                        "coverage_ratio": round(coverage_ratio, 2),
                        "lanes_covered": lanes_covered,
                        "total_lanes": len(LANES),
                        "rank_balance": round(rank_balance, 2),
                        "rank_balance_weight": 0.20,
                        "rank_balance_contribution": round(rank_balance * 0.20, 2),
                        "skill_balance": round(skill_balance, 2),
                        "skill_balance_weight": 0.40,
                        "skill_balance_contribution": round(skill_balance * 0.40, 2),
                        "skill_std": round(skill_std, 2),
                        "rank_std": round(rank_std, 2),
                        "avg_skill": round(avg_skill, 2),
                        "global_avg_skill": round(global_avg, 2),
                        "skill_deviation": round(skill_deviation, 2),
                        "min_skill": round(float(np.min(skill_scores)), 2) if skill_scores else 0.0,
                        "max_skill": round(float(np.max(skill_scores)), 2) if skill_scores else 0.0,
                    },
                )
            )
            fairness_scores.append(fairness)
        if not fairness_scores:
            return 0.0, 0.0, [], 0.0
        mean_fairness = float(np.mean(fairness_scores))
        min_fairness = float(np.min(fairness_scores))
        fairness_std = float(np.std(fairness_scores))
        return mean_fairness, min_fairness, team_results, fairness_std

    def optimize(self) -> Tuple[List[TeamResult], int, float]:
        best_teams = None
        best_score = -float("inf")
        iterations = 0
        no_improve_count = 0
        auto_max_iterations = min(50, self.config.max_iterations)
        shortage_roles = self.analyzer.get_shortage_roles(len(self.participants))
        for iteration in range(auto_max_iterations):
            candidates = self.rand_engine.generate_candidates(self.participants, self.num_teams, shortage_roles)
            if not candidates:
                break
            final_teams = self.rand_engine.pick_final_team(candidates)
            if not final_teams:
                continue
            
            # HARD CONSTRAINT: Skip candidates where any team is missing a lane
            all_roles = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]
            invalid = False
            for team in final_teams:
                if not team:
                    invalid = True
                    break
                if len(team) != self.config.team_size:
                    invalid = True
                    break
                lanes = {lane for _, lane in team}
                if len(lanes) != 5:
                    invalid = True
                    break
            if invalid:
                continue
            
            for team in final_teams:
                self.history.record_team(team)
            mean_fairness, min_fairness, team_results, fairness_std = self._score_teams_multi_objective(final_teams)
            iterations += 1
            skill_avgs = [float(np.mean([p.skill_score for p, _ in t])) for t in final_teams if t]
            skill_std = float(np.std(skill_avgs)) if skill_avgs else 0.0
            score = min_fairness - fairness_std * 3.0 - skill_std * 20.0
            if score > best_score:
                best_score = score
                best_teams = team_results
                no_improve_count = 0
            else:
                no_improve_count += 1
            if min_fairness >= 90.0 and fairness_std < 3.0 and skill_std < 2.0:
                break
            if no_improve_count >= 15:
                break
        if best_teams is None:
            final_teams = self.rand_engine._generate_single_candidate(self.participants, self.num_teams, shortage_roles)
            if not final_teams:
                snake_teams = self._role_aware_snake_draft(self.participants)
                filled_teams = self._fill_missing_roles(snake_teams)
                final_teams = [self._optimize_lanes_preference_first(t) for t in filled_teams]
            else:
                raw_teams = [[p for p, _ in team] for team in final_teams]
                filled_teams = self._fill_missing_roles(raw_teams)
                final_teams = [self._optimize_lanes_preference_first(t) for t in filled_teams]
            _, _, best_teams, _ = self._score_teams_multi_objective(final_teams)
            best_score = float(np.min([t.overall_fairness for t in best_teams])) if best_teams else 0.0
        
        # Post-process: balance skill/comfort/fairness across teams while preserving lane assignments
        if best_teams and len(best_teams) > 1:
            best_teams = self._balance_teams_efficiently(best_teams)
        
        return best_teams, iterations, best_score

    def _balance_teams_efficiently(self, team_results: List[TeamResult]) -> List[TeamResult]:
        if len(team_results) <= 1:
            return team_results
        
        teams = [list(t.players) for t in team_results]
        
        # Precompute team metrics
        def team_metrics(ti: int):
            t = teams[ti]
            avg_skill = float(np.mean([p.skill_score for p in t])) if t else 0.0
            return avg_skill
        
        metrics = [team_metrics(ti) for ti in range(len(teams))]
        skill_vals = [m for m in metrics]
        
        # Target: balance skill across teams
        target_skill = float(np.mean(skill_vals))
        
        # Single pass: try swapping players between teams to reduce imbalance
        for _ in range(5):
            improved = False
            for i in range(len(teams)):
                for j in range(i + 1, len(teams)):
                    if len(teams[i]) != len(teams[j]):
                        continue
                    for pi in range(len(teams[i])):
                        for pj in range(len(teams[j])):
                            p1 = teams[i][pi]
                            p2 = teams[j][pj]
                            
                            # Skip if players have the same assigned lane (swap is pointless)
                            if p1.assigned_lane == p2.assigned_lane:
                                continue
                            
                            # Check that both teams would still have all 5 lanes after swap
                            lanes_i = {p.assigned_lane for p in teams[i]}
                            lanes_j = {p.assigned_lane for p in teams[j]}
                            lanes_i_after = lanes_i - {p1.assigned_lane} | {p2.assigned_lane}
                            lanes_j_after = lanes_j - {p2.assigned_lane} | {p1.assigned_lane}
                            if len(lanes_i_after) < 5 or len(lanes_j_after) < 5:
                                continue
                            
                            # Compute current imbalance
                            skill1 = skill_vals[i]
                            skill2 = skill_vals[j]
                            
                            # After swap
                            new_skill1 = (skill1 * len(teams[i]) - p1.skill_score + p2.skill_score) / len(teams[i])
                            new_skill2 = (skill2 * len(teams[j]) - p2.skill_score + p1.skill_score) / len(teams[j])
                            
                            # Check if swap improves overall balance
                            current_var = (skill1 - target_skill)**2 + (skill2 - target_skill)**2
                            new_var = (new_skill1 - target_skill)**2 + (new_skill2 - target_skill)**2
                            
                            if new_var < current_var:
                                teams[i][pi], teams[j][pj] = teams[j][pj], teams[i][pi]
                                skill_vals[i] = new_skill1
                                skill_vals[j] = new_skill2
                                improved = True
                                break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
            if not improved:
                break
        
        balanced_results = []
        for idx, team_players in enumerate(teams):
            avg_skill = float(np.mean([p.skill_score for p in team_players]))
            skill_std = float(np.std([p.skill_score for p in team_players]))
            skill_deviation = abs(avg_skill - float(np.mean([p.skill_score for p in self.participants]))) if self.participants else 0.0
            skill_balance = float(max(0.0, 100.0 - skill_deviation * 3.0))
            role_balance = team_results[idx].role_balance_score
            rank_balance = 0.0
            rank_scores = [self._get_rank_score(p) for p in team_players]
            if rank_scores:
                rank_std = float(np.std(rank_scores))
                rank_balance = float(max(0.0, 100.0 - rank_std * 5.0))
            fairness = (
                role_balance * 0.40
                + rank_balance * 0.20
                + skill_balance * 0.40
            )
            balanced_results.append(
                TeamResult(
                    team_id=team_results[idx].team_id,
                    players=team_players,
                    average_skill_score=round(avg_skill, 2),
                    role_balance_score=round(role_balance, 2),
                    comfort_score=0.0,
                    overall_fairness=round(fairness, 2),
                    fairness_breakdown={
                        "role_balance": round(role_balance, 2),
                        "role_balance_weight": 0.40,
                        "role_balance_contribution": round(role_balance * 0.40, 2),
                        "coverage_ratio": round(team_results[idx].fairness_breakdown.get("coverage_ratio", 1.0), 2),
                        "lanes_covered": team_results[idx].fairness_breakdown.get("lanes_covered", 5),
                        "total_lanes": team_results[idx].fairness_breakdown.get("total_lanes", 5),
                        "rank_balance": round(rank_balance, 2),
                        "rank_balance_weight": 0.20,
                        "rank_balance_contribution": round(rank_balance * 0.20, 2),
                        "skill_balance": round(skill_balance, 2),
                        "skill_balance_weight": 0.40,
                        "skill_balance_contribution": round(skill_balance * 0.40, 2),
                        "skill_std": round(skill_std, 2),
                        "rank_std": round(rank_std, 2) if rank_scores else 0.0,
                        "avg_skill": round(avg_skill, 2),
                        "global_avg_skill": round(float(np.mean([p.skill_score for p in self.participants])), 2) if self.participants else 0.0,
                        "skill_deviation": round(skill_deviation, 2),
                        "min_skill": round(float(np.min([p.skill_score for p in team_players])), 2) if team_players else 0.0,
                        "max_skill": round(float(np.max([p.skill_score for p in team_players])), 2) if team_players else 0.0,
                    },
                )
            )
        return balanced_results

    def _role_aware_snake_draft(self, players: List[ParticipantFeatures]) -> List[List[ParticipantFeatures]]:
        teams: List[List[ParticipantFeatures]] = [[] for _ in range(self.num_teams)]
        team_skills = [0.0 for _ in range(self.num_teams)]
        team_ranks = [0.0 for _ in range(self.num_teams)]
        player_idx = 0
        while player_idx < len(players) and any(len(t) < 5 for t in teams):
            round_num = player_idx // self.num_teams
            is_reverse = round_num % 2 == 1
            team_order = list(range(self.num_teams - 1, -1, -1)) if is_reverse else list(range(self.num_teams))
            eligible_teams = [ti for ti in team_order if len(teams[ti]) < 5]
            if not eligible_teams:
                break
            player = players[player_idx]

            def team_score(ti):
                team_roles = self._get_team_roles(teams[ti])
                missing_roles = 0
                if player.primary_lane in LANES and player.primary_lane not in team_roles:
                    missing_roles += 1
                if player.secondary_lane and player.secondary_lane in LANES and player.secondary_lane not in team_roles:
                    missing_roles += 1
                return (-missing_roles * 200.0, -self._get_rank_score(player) * 10.0, team_skills[ti], team_ranks[ti], ti)

            best_team = min(eligible_teams, key=team_score)
            teams[best_team].append(player)
            team_skills[best_team] += player.skill_score
            team_ranks[best_team] += self._get_rank_score(player)
            player_idx += 1
        return teams

    def _get_team_roles(self, team: List[ParticipantFeatures]) -> set:
        roles = set()
        for p in team:
            if p.primary_lane in LANES:
                roles.add(p.primary_lane)
            if p.secondary_lane and p.secondary_lane in LANES:
                roles.add(p.secondary_lane)
        return roles

    def _fill_missing_roles(self, teams: List[List[ParticipantFeatures]]) -> List[List[ParticipantFeatures]]:
        filled_teams = [list(t) for t in teams]
        target_size = 5
        for team in filled_teams:
            if len(team) < target_size:
                current_roles = self._get_team_roles(team)
                missing_roles = [lane for lane in LANES if lane not in current_roles]
                if not missing_roles:
                    continue
                candidates = []
                for p in self.participants:
                    if p in team:
                        continue
                    if p.primary_lane in missing_roles or p.secondary_lane in missing_roles:
                        candidates.append((p, 1.0, p.skill_score))
                    else:
                        candidates.append((p, 0.0, p.skill_score))
                if not candidates:
                    continue
                candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                for missing_role in missing_roles:
                    if len(team) >= target_size:
                        break
                    role_candidates = [(p, w, s) for p, w, s in candidates if p.primary_lane == missing_role or p.secondary_lane == missing_role]
                    if not role_candidates:
                        role_candidates = [(p, w, s) for p, w, s in candidates if p.primary_lane not in LANES and (p.secondary_lane is None or p.secondary_lane not in LANES)]
                    if not role_candidates:
                        role_candidates = candidates
                    role_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                    best_player = role_candidates[0][0]
                    team.append(best_player)
                    candidates = [(p, w, s) for p, w, s in candidates if p.player_id != best_player.player_id]
        
        # Post-process: fix teams with 5 players but missing lanes by swapping
        changed = True
        max_swap_rounds = 20
        round_num = 0
        while changed and round_num < max_swap_rounds:
            changed = False
            round_num += 1
            for team in filled_teams:
                if len(team) != target_size:
                    continue
                current_roles = self._get_team_roles(team)
                missing_roles = [lane for lane in LANES if lane not in current_roles]
                if not missing_roles:
                    continue
                for missing_role in missing_roles:
                    for other_team in filled_teams:
                        if other_team is team:
                            continue
                        for i, p in enumerate(other_team):
                            if p.primary_lane == missing_role or p.secondary_lane == missing_role:
                                for j, q in enumerate(team):
                                    q_roles = set()
                                    if q.primary_lane in LANES:
                                        q_roles.add(q.primary_lane)
                                    if q.secondary_lane and q.secondary_lane in LANES:
                                        q_roles.add(q.secondary_lane)
                                    q_duplicate = False
                                    for k, r in enumerate(team):
                                        if k != j and (r.primary_lane in q_roles or r.secondary_lane in q_roles):
                                            q_duplicate = True
                                            break
                                    if q_duplicate:
                                        team[j], other_team[i] = p, q
                                        changed = True
                                        break
                                if changed:
                                    break
                        if changed:
                            break
                    if changed:
                        break
        
        return filled_teams

    def _optimize_lanes_preference_first(self, team_players: List[ParticipantFeatures]) -> List[Tuple[ParticipantFeatures, str]]:
        if len(team_players) <= 1:
            return [(p, p.primary_lane if p.primary_lane in LANES else LANES[0]) for p in team_players]
        n = min(len(team_players), len(LANES))
        players = team_players[:n]
        best_score = -float("inf")
        best_assignment: List[Tuple[ParticipantFeatures, str]] = []
        for perm in permutations(LANES, n):
            score = 0.0
            for i, player in enumerate(players):
                lane = perm[i]
                if lane == player.primary_lane or lane == player.secondary_lane:
                    score += 1000.0
            if score > best_score:
                best_score = score
                best_assignment = [(players[i], perm[i]) for i in range(n)]
        return best_assignment
