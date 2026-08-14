from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import json
import ast
import os
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.ranking_repository import RankingRepository
from app.repositories.system_state_repository import SystemStateRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.team_service import TeamFormationService
from app.schemas.schemas import (
    ParticipantFeatures, RankingResponse, RankingPreviewResponse,
    ParticipantStatus, SystemState as SystemStateEnum,
)
from app.config.settings import settings


def _get_master_csv_path() -> str:
    path = settings.master_csv_path
    if os.path.isabs(path):
        return path
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)


class RankingService:
    def __init__(
        self,
        participant_repo: ParticipantRepository,
        ranking_repo: RankingRepository,
        system_state_repo: SystemStateRepository,
        audit_repo: AuditRepository,
        payment_repo: PaymentRepository,
        team_service: TeamFormationService,
    ):
        self.participant_repo = participant_repo
        self.ranking_repo = ranking_repo
        self.system_state_repo = system_state_repo
        self.audit_repo = audit_repo
        self.payment_repo = payment_repo
        self.team_service = team_service

    async def load_and_validate_participants(self) -> Dict[str, Any]:
        db_path = _get_master_csv_path()
        import pandas as pd

        df = pd.read_csv(db_path, dtype=str, keep_default_na=False,
                         na_values=["", "NA", "N/A", "null", "None", "nan", "NaN"])
        df.columns = [c.strip() for c in df.columns]
        df = df.replace("", pd.NA)
        validation = self.team_service.validate_csv(df)

        if not validation.is_valid:
            return {
                "is_valid": False,
                "total_rows": validation.total_rows,
                "valid_participants": validation.valid_participants,
                "invalid_participants": validation.invalid_participants,
                "missing_fields": validation.missing_fields,
                "invalid_records": validation.invalid_records,
                "duplicate_records": validation.duplicate_records,
            }

        participants = self.team_service.process_features()
        participant_dicts = []
        for p in participants:
            participant_dicts.append({
                "id": p.player_id,
                "name": p.name,
                "email": p.email,
                "username": p.username,
                "current_rank": p.current_rank,
                "current_stars": p.current_stars,
                "highest_rank": p.highest_rank,
                "highest_stars": p.highest_stars,
                "primary_lane": p.primary_lane,
                "primary_lane_comfort": p.primary_lane_comfort,
                "secondary_lane": p.secondary_lane,
                "secondary_lane_comfort": p.secondary_lane_comfort,
                "skill_score": p.skill_score,
                "current_rank_score": p.current_rank_score,
                "current_star_score": p.current_star_score,
                "highest_rank_score": p.highest_rank_score,
                "highest_star_score": p.highest_star_score,
                "role_flexibility_score": p.role_flexibility_score,
                "jungle_comfort": p.jungle_comfort,
                "exp_comfort": p.exp_comfort,
                "mid_comfort": p.mid_comfort,
                "gold_comfort": p.gold_comfort,
                "roam_comfort": p.roam_comfort,
                "lane_capabilities": json.dumps(p.lane_capabilities),
                "status": ParticipantStatus.registered.value,
            })

        existing_ids = {p.id for p in await self.participant_repo.get_all()}
        new_participants = [p for p in participant_dicts if p["id"] not in existing_ids]

        if new_participants:
            await self.participant_repo.upsert_many(participant_dicts)
        else:
            for p in participant_dicts:
                await self.participant_repo.upsert_many([p])

        return {
            "is_valid": True,
            "total_rows": validation.total_rows,
            "valid_participants": validation.valid_participants,
            "invalid_participants": validation.invalid_participants,
            "missing_fields": validation.missing_fields,
            "invalid_records": validation.invalid_records,
            "duplicate_records": validation.duplicate_records,
            "participants": participants,
        }

    def _deterministic_sort_key(self, p: ParticipantFeatures) -> tuple:
        return (
            -p.skill_score,
            -p.role_flexibility_score,
            p.player_id,
        )

    def _calculate_qualified_eliminated(self, total: int) -> tuple:
        qualified_count = (total // 5) * 5
        eliminated_count = total - qualified_count
        return qualified_count, eliminated_count

    async def generate_ranking(self, actor: Optional[str] = None) -> Dict[str, Any]:
        result = await self.load_and_validate_participants()
        if not result.get("is_valid"):
            return result

        participants: List[ParticipantFeatures] = result["participants"]
        ranked = sorted(participants, key=self._deterministic_sort_key)

        qualified_count, eliminated_count = self._calculate_qualified_eliminated(len(ranked))

        for idx, p in enumerate(ranked, start=1):
            p.rank = idx
            if idx <= qualified_count:
                p.status = ParticipantStatus.qualified.value
            else:
                p.status = ParticipantStatus.eliminated.value
            p.skill_score_breakdown = {
                "current_rank_component": (p.current_rank_score or 0.0) * settings.current_rank_weight,
                "current_star_component": (p.current_star_score or 0.0) * settings.current_star_weight,
                "highest_rank_component": (p.highest_rank_score or 0.0) * settings.highest_rank_weight,
                "highest_star_component": (p.highest_star_score or 0.0) * settings.highest_star_weight,
            }
            p.role_flexibility_breakdown = {
                "primary_comfort": p.primary_lane_comfort or 0,
                "secondary_comfort": p.secondary_lane_comfort or 0,
                "normalized_primary": ((p.primary_lane_comfort or 0) / 5.0) * 100,
            }
            await self.participant_repo.update_status(p.player_id, p.status)
            await self.participant_repo.update_rank(p.player_id, idx)

        active_ranking = await self.ranking_repo.get_active()
        if active_ranking:
            await self.ranking_repo.deactivate_all()

        version_id = str(uuid4())
        score_components = {
            "current_rank_weight": 0.40,
            "current_star_weight": 0.20,
            "highest_rank_weight": 0.25,
            "highest_star_weight": 0.15,
        }
        ranking_version = await self.ranking_repo.create(
            version_id=version_id,
            total_participants=len(ranked),
            qualified_count=qualified_count,
            eliminated_count=eliminated_count,
            generated_by=actor,
            seed=42,
            score_components=str(score_components),
        )

        await self.audit_repo.create(
            action="RANKING_GENERATED",
            actor=actor,
            metadata={
                "ranking_version_id": version_id,
                "total_participants": len(ranked),
                "qualified_count": qualified_count,
                "eliminated_count": eliminated_count,
            },
        )

        await self.system_state_repo.update_state(
            SystemStateEnum.ranking_generated.value,
            ranking_version_id=version_id,
        )

        return {
            "is_valid": True,
            "ranking_version_id": version_id,
            "rankings": ranked,
            "total": len(ranked),
            "qualified_count": qualified_count,
            "eliminated_count": eliminated_count,
            "score_components": score_components,
            "generated_at": ranking_version.generated_at.isoformat(),
            "status": ranking_version.status,
        }

    async def get_rankings(self) -> Dict[str, Any]:
        state_ok = await self.system_state_repo.get_or_create()
        if state_ok.state == SystemStateEnum.draft.value:
            return {
                "rankings": [],
                "total": 0,
                "qualified_count": 0,
                "eliminated_count": 0,
                "generated_at": None,
                "score_components": None,
                "status": "NOT_AVAILABLE",
            }

        active_ranking = await self.ranking_repo.get_active()
        if not active_ranking:
            return {
                "rankings": [],
                "total": 0,
                "qualified_count": 0,
                "eliminated_count": 0,
                "generated_at": None,
                "score_components": None,
                "status": "NOT_AVAILABLE",
            }

        participants = await self.participant_repo.get_all()
        ranked = sorted(
            [p for p in participants if p.rank is not None],
            key=lambda p: p.rank or 0,
        )

        ranked_response = []
        for p in ranked:
            lane_caps = {}
            if p.lane_capabilities:
                try:
                    lane_caps = ast.literal_eval(p.lane_capabilities)
                except Exception:
                    lane_caps = {}

            ranked_response.append(ParticipantFeatures(
                player_id=p.id,
                name=p.name,
                full_name=p.name,
                email=p.email,
                username=p.username,
                current_rank=p.current_rank,
                current_stars=p.current_stars,
                highest_rank=p.highest_rank,
                highest_stars=p.highest_stars,
                current_rank_score=p.current_rank_score or 0.0,
                current_star_score=p.current_star_score or 0.0,
                highest_rank_score=p.highest_rank_score or 0.0,
                highest_star_score=p.highest_star_score or 0.0,
                primary_lane=p.primary_lane,
                secondary_lane=p.secondary_lane,
                primary_lane_comfort=p.primary_lane_comfort,
                secondary_lane_comfort=p.secondary_lane_comfort,
                skill_score=p.skill_score or 0.0,
                role_flexibility_score=p.role_flexibility_score or 0.0,
                jungle_comfort=p.jungle_comfort or 0.0,
                exp_comfort=p.exp_comfort or 0.0,
                mid_comfort=p.mid_comfort or 0.0,
                gold_comfort=p.gold_comfort or 0.0,
                roam_comfort=p.roam_comfort or 0.0,
                lane_capabilities=lane_caps,
                rank=p.rank,
                status=p.status,
                skill_score_breakdown={
                    "current_rank_component": (p.current_rank_score or 0.0) * settings.current_rank_weight,
                    "current_star_component": (p.current_star_score or 0.0) * settings.current_star_weight,
                    "highest_rank_component": (p.highest_rank_score or 0.0) * settings.highest_rank_weight,
                    "highest_star_component": (p.highest_star_score or 0.0) * settings.highest_star_weight,
                },
                role_flexibility_breakdown={
                    "primary_comfort": p.primary_lane_comfort or 0,
                    "secondary_comfort": p.secondary_lane_comfort or 0,
                    "normalized_primary": ((p.primary_lane_comfort or 0) / 5.0) * 100,
                },
            ))

        score_components = None
        if active_ranking.score_components:
            try:
                score_components = eval(active_ranking.score_components)
            except Exception:
                score_components = None

        return {
            "rankings": ranked_response,
            "total": len(ranked_response),
            "qualified_count": active_ranking.qualified_count,
            "eliminated_count": active_ranking.eliminated_count,
            "generated_at": active_ranking.generated_at.isoformat(),
            "score_components": score_components,
            "status": active_ranking.status,
        }

    async def get_ranking_versions(self) -> List[Dict[str, Any]]:
        versions = await self.ranking_repo.get_all()
        return [
            {
                "id": v.id,
                "generated_at": v.generated_at.isoformat(),
                "confirmed_at": v.confirmed_at.isoformat() if v.confirmed_at else None,
                "status": v.status,
                "total_participants": v.total_participants,
                "qualified_count": v.qualified_count,
                "eliminated_count": v.eliminated_count,
                "generated_by": v.generated_by,
                "is_active": v.is_active,
            }
            for v in versions
        ]

    async def confirm_ranking(self, version_id: str, actor: Optional[str] = None) -> Dict[str, Any]:
        version = await self.ranking_repo.confirm(version_id)
        if not version:
            return {"success": False, "message": "Ranking version not found"}

        await self.audit_repo.create(
            action="RANKING_CONFIRMED",
            actor=actor,
            metadata={"ranking_version_id": version_id},
        )
        return {
            "success": True,
            "ranking_version_id": version_id,
            "status": version.status,
            "confirmed_at": version.confirmed_at.isoformat() if version.confirmed_at else None,
        }
