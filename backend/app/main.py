from fastapi import FastAPI, HTTPException, Depends, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
import asyncio
import pandas as pd
import json
import ast
import traceback
import secrets
import os
from uuid import uuid4
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.config.settings import settings
from app.schemas.schemas import (
    AdminGenerateRankingRequest,
    AdminGenerateTeamRequest,
    PaymentVerificationRequest,
    SystemStateResponse,
    AdminDashboardStats,
)
from app.services.team_service import TeamFormationService
from app.services.ranking_service import RankingService
from app.services.storage_service import storage_service
from app.api.deps import get_current_user, get_admin_user, create_access_token, decode_token


def _build_skill_breakdown(skill_score: float, current_rank_score: Optional[float], current_star_score: Optional[float], highest_rank_score: Optional[float], highest_star_score: Optional[float]) -> Dict[str, Any]:
    total = skill_score or 0.0
    cr = current_rank_score if current_rank_score is not None else 0.0
    cs = current_star_score if current_star_score is not None else 0.0
    hr = highest_rank_score if highest_rank_score is not None else 0.0
    hs = highest_star_score if highest_star_score is not None else 0.0

    raw_total = cr + cs + hr + hs
    components = {
        "current_rank": {
            "raw_score": round(cr, 4),
            "weight": settings.current_rank_weight,
            "weight_percent": round(settings.current_rank_weight * 100, 2),
            "contribution": round(cr * settings.current_rank_weight, 4),
            "formula": f"{round(cr, 4)} × {settings.current_rank_weight} = {round(cr * settings.current_rank_weight, 4)}",
        },
        "current_star": {
            "raw_score": round(cs, 4),
            "weight": settings.current_star_weight,
            "weight_percent": round(settings.current_star_weight * 100, 2),
            "contribution": round(cs * settings.current_star_weight, 4),
            "formula": f"{round(cs, 4)} × {settings.current_star_weight} = {round(cs * settings.current_star_weight, 4)}",
        },
        "highest_rank": {
            "raw_score": round(hr, 4),
            "weight": settings.highest_rank_weight,
            "weight_percent": round(settings.highest_rank_weight * 100, 2),
            "contribution": round(hr * settings.highest_rank_weight, 4),
            "formula": f"{round(hr, 4)} × {settings.highest_rank_weight} = {round(hr * settings.highest_rank_weight, 4)}",
        },
        "highest_star": {
            "raw_score": round(hs, 4),
            "weight": settings.highest_star_weight,
            "weight_percent": round(settings.highest_star_weight * 100, 2),
            "contribution": round(hs * settings.highest_star_weight, 4),
            "formula": f"{round(hs, 4)} × {settings.highest_star_weight} = {round(hs * settings.highest_star_weight, 4)}",
        },
    }

    return {
        "total_skill_score": round(total, 4),
        "raw_total": round(raw_total, 4),
        "final_score": round(raw_total, 4),
        "components": components,
        "weights": {
            "current_rank": settings.current_rank_weight,
            "current_star": settings.current_star_weight,
            "highest_rank": settings.highest_rank_weight,
            "highest_star": settings.highest_star_weight,
        },
        "calculation": f"({round(cr, 4)} × {settings.current_rank_weight}) + ({round(cs, 4)} × {settings.current_star_weight}) + ({round(hr, 4)} × {settings.highest_rank_weight}) + ({round(hs, 4)} × {settings.highest_star_weight}) = {round(raw_total, 4)}",
    }


def _build_role_breakdown(primary_lane_comfort: Optional[int], secondary_lane_comfort: Optional[int]) -> Dict[str, Any]:
    primary = primary_lane_comfort or 0
    secondary = secondary_lane_comfort or 0

    normalized_primary = (primary / 5.0) * 100
    normalized_secondary = (secondary / 5.0) * 100 if secondary is not None else 0.0

    primary_weight = 0.70
    secondary_weight = 0.30

    primary_contribution = normalized_primary * primary_weight
    secondary_contribution = normalized_secondary * secondary_weight if secondary is not None else 0.0
    flexibility_score = primary_contribution + secondary_contribution

    return {
        "primary_comfort": primary,
        "secondary_comfort": secondary if secondary is not None else 0,
        "normalized_primary": round(normalized_primary, 2),
        "normalized_secondary": round(normalized_secondary, 2) if secondary is not None else 0.0,
        "primary_weight": primary_weight,
        "secondary_weight": secondary_weight,
        "primary_weight_percent": round(primary_weight * 100, 2),
        "secondary_weight_percent": round(secondary_weight * 100, 2),
        "primary_contribution": round(primary_contribution, 4),
        "secondary_contribution": round(secondary_contribution, 4),
        "flexibility_score": round(flexibility_score, 4),
        "components": {
            "primary": {
                "comfort": primary,
                "normalized": round(normalized_primary, 2),
                "weight": primary_weight,
                "weight_percent": round(primary_weight * 100, 2),
                "contribution": round(primary_contribution, 4),
                "formula": f"{round(normalized_primary, 2)}% × {primary_weight} = {round(primary_contribution, 4)}",
            },
            "secondary": {
                "comfort": secondary if secondary is not None else 0,
                "normalized": round(normalized_secondary, 2) if secondary is not None else 0.0,
                "weight": secondary_weight,
                "weight_percent": round(secondary_weight * 100, 2),
                "contribution": round(secondary_contribution, 4),
                "formula": f"{round(normalized_secondary, 2)}% × {secondary_weight} = {round(secondary_contribution, 4)}",
            },
        },
        "calculation": f"({round(normalized_primary, 2)}% × {primary_weight}) + ({round(normalized_secondary, 2)}% × {secondary_weight}) = {round(flexibility_score, 4)}",
    }
from app.services.payment_service import PaymentService
from app.services.system_state_service import SystemStateService
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.ranking_repository import RankingRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.system_state_repository import SystemStateRepository
from app.repositories.audit_repository import AuditRepository
from app.database import get_db, init_db, Base, engine
from app.tournament.routers.admin_tournament import router as admin_tournament_router
from app.tournament.routers.user_tournament import router as user_tournament_router
service = TeamFormationService()


class LoginRequest(BaseModel):
    email: str


def _require_admin(x_user_token: Optional[str]) -> dict:
    if not x_user_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        payload = decode_token(x_user_token)
    except HTTPException:
        raise HTTPException(status_code=403, detail="Forbidden")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return payload


def _require_user(x_user_token: Optional[str]) -> dict:
    if not x_user_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return decode_token(x_user_token)


def _get_master_csv_path() -> str:
    path = settings.master_csv_path
    if os.path.isabs(path):
        return path
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)


def _load_default_database():
    db_path = _get_master_csv_path()
    try:
        df = pd.read_csv(db_path, dtype=str, keep_default_na=False, na_values=["", "NA", "N/A", "null", "None", "nan", "NaN"])
        df.columns = [c.strip() for c in df.columns]
        df = df.replace("", pd.NA)
        service.validate_csv(df)
        service.process_features()
    except Exception as e:
        print(f"Failed to load default database: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_payments_created_at ON payments(created_at DESC)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_team_members_team_id ON team_members(team_id)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_participants_status_rank ON participants(status, rank)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_payments_status_created_at ON payments(status, created_at DESC)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_team_members_version_team ON team_members(team_version_id, team_id)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_audit_logs_action_timestamp ON audit_logs(action, timestamp DESC)")
            )
            await conn.execute(
                text("ALTER TABLE matches ADD COLUMN IF NOT EXISTS next_match_id VARCHAR NULL")
            )
            await conn.execute(
                text("ALTER TABLE matches ADD COLUMN IF NOT EXISTS loser_next_match_id VARCHAR NULL")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_matches_next_match_id ON matches(next_match_id)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_matches_loser_next_match_id ON matches(loser_next_match_id)")
            )
    except Exception as e:
        print(f"Startup warning: database initialization failed: {e}")
    yield


app = FastAPI(
    title="ML Fair Team Formation System",
    description="API for fair Mobile Legends team formation",
    version="1.0.0",
    lifespan=lifespan,
)


class SimpleCache:
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}

    def get(self, key: str) -> Any:
        if key in self._store:
            if datetime.utcnow() < self._expiry.get(key, datetime.min):
                return self._store[key]
            self.invalidate(key)
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        self._store[key] = value
        self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)
        self._expiry.pop(key, None)


cache = SimpleCache()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_tournament_router)
app.include_router(user_tournament_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail} if isinstance(exc.detail, str) else {"detail": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    if settings.debug:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {str(exc)}"})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root():
    return {"message": "ML Fair Team Formation System API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = request.email.strip().lower()

    if email in settings.admin_emails_list:
        token = create_access_token({"sub": "admin", "email": email, "role": "admin", "name": "Admin"})
        return {
            "token": token,
            "player_id": "admin",
            "email": email,
            "username": None,
            "full_name": "Admin",
            "name": "Admin",
            "role": "admin",
        }

    repo = ParticipantRepository(db)
    participant = await repo.get_by_email(email)
    if not participant:
        raise HTTPException(status_code=400, detail="Email tidak ditemukan")

    token = create_access_token({"sub": participant.id, "email": participant.email, "role": "user", "name": participant.name})

    return {
        "token": token,
        "player_id": participant.id,
        "email": participant.email,
        "username": participant.username,
        "full_name": participant.name,
        "name": participant.name,
        "role": "user",
    }


@app.post("/api/admin/process-participants")
async def admin_process_participants(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    db_path = _get_master_csv_path()
    try:
        df = pd.read_csv(db_path, dtype=str, keep_default_na=False, na_values=["", "NA", "N/A", "null", "None", "nan", "NaN"])
        df.columns = [c.strip() for c in df.columns]
        df = df.replace("", pd.NA)
        validation = service.validate_csv(df)
        if not validation.is_valid:
            raise HTTPException(status_code=400, detail="CSV tidak valid")
        participants = service.process_features()
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
                "status": "REGISTERED",
            })
        repo = ParticipantRepository(db)
        await repo.clear_all()
        await db.execute(text("DELETE FROM payments"))
        await db.execute(text("DELETE FROM team_members"))
        await db.flush()
        await repo.upsert_many(participant_dicts)
        await db.commit()
        count = len(await repo.get_all())
        cache.invalidate("admin_dashboard")
        cache.invalidate("admin_rankings")
        cache.invalidate("rankings_public")
        cache.invalidate("admin_ranking_versions")
        cache.invalidate("admin_payments")
        cache.invalidate("admin_audit_log")
        cache.invalidate("admin_team_versions")
        return {
            "message": "Participants processed",
            "count": count,
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.get("/api/me/ranking")
async def get_my_ranking(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_user(x_user_token)

    player_id = decode_token(x_user_token)["sub"]

    repo = ParticipantRepository(db)
    participant = await repo.get_by_id(player_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Player not found")

    if participant.rank is None:
        raise HTTPException(status_code=404, detail="Ranking belum digenerate oleh admin.")

    import json
    lane_caps = {}
    if participant.lane_capabilities:
        try:
            lane_caps = ast.literal_eval(participant.lane_capabilities)
        except Exception:
            lane_caps = {}

    return {
        "rank": participant.rank,
        "total": await repo.count(),
        "player": {
            "player_id": participant.id,
            "name": participant.name,
            "full_name": participant.name,
            "email": participant.email,
            "username": participant.username,
            "current_rank": participant.current_rank,
            "current_stars": participant.current_stars,
            "highest_rank": participant.highest_rank,
            "highest_stars": participant.highest_stars,
            "current_rank_score": participant.current_rank_score or 0.0,
            "current_star_score": participant.current_star_score or 0.0,
            "highest_rank_score": participant.highest_rank_score or 0.0,
            "highest_star_score": participant.highest_star_score or 0.0,
            "primary_lane": participant.primary_lane,
            "secondary_lane": participant.secondary_lane,
            "primary_lane_comfort": participant.primary_lane_comfort,
            "secondary_lane_comfort": participant.secondary_lane_comfort,
            "skill_score": participant.skill_score or 0.0,
            "role_flexibility_score": participant.role_flexibility_score or 0.0,
            "jungle_comfort": participant.jungle_comfort or 0.0,
            "exp_comfort": participant.exp_comfort or 0.0,
            "mid_comfort": participant.mid_comfort or 0.0,
            "gold_comfort": participant.gold_comfort or 0.0,
            "roam_comfort": participant.roam_comfort or 0.0,
            "lane_capabilities": lane_caps,
            "rank": participant.rank,
            "status": participant.status,
            "skill_score_breakdown": _build_skill_breakdown(
                participant.skill_score or 0.0,
                participant.current_rank_score,
                participant.current_star_score,
                participant.highest_rank_score,
                participant.highest_star_score,
            ),
            "role_flexibility_breakdown": _build_role_breakdown(participant.primary_lane_comfort, participant.secondary_lane_comfort),
        },
    }


@app.get("/api/me/team")
async def get_my_team(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_user(x_user_token)

    player_id = decode_token(x_user_token)["sub"]

    repo = ParticipantRepository(db)
    participant = await repo.get_by_id(player_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Player not found")

    if participant.status == "ELIMINATED":
        return {
            "team_id": None,
            "team": None,
            "message": "Anda tidak lolos karena jumlah peserta yang lolos harus merupakan kelipatan 5.",
        }

    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.repositories.team_repository import TeamRepository
    from app.schemas.schemas import SystemState as SystemStateEnum

    payment_repo = PaymentRepository(db)
    state_repo = SystemStateRepository(db)
    team_repo = TeamRepository(db)

    payment = await payment_repo.get_by_player_id(player_id)
    if not payment or payment.status != "PAID":
        return {
            "team_id": None,
            "team": None,
            "message": "Pembayaran belum dilakukan. Silakan upload bukti pembayaran untuk melihat tim.",
        }

    participant_repo = ParticipantRepository(db)
    qualified = await participant_repo.get_by_status("QUALIFIED")
    qualified_ids = [p.id for p in qualified]
    payments = await payment_repo.get_by_player_ids(qualified_ids)
    paid_ids = {p.player_id for p in payments if p.status == "PAID"}
    unpaid = [p.name or p.id for p in qualified if p.id not in paid_ids]
    if unpaid:
        return {
            "team_id": None,
            "team": None,
            "message": "Menunggu pembayaran dari beberapa peserta. Semua peserta lolos kualifikasi harus membayar sebelum tim ditampilkan.",
            "unpaid": unpaid,
        }

    state = await state_repo.get_or_create()
    if state.state not in [
        SystemStateEnum.team_generated.value,
        SystemStateEnum.payment_open.value,
        SystemStateEnum.competition_ready.value,
    ]:
        return {
            "team_id": None,
            "team": None,
            "message": "Team belum digenerate oleh admin.",
        }

    team_version = await team_repo.get_active()
    if not team_version:
        return {
            "team_id": None,
            "team": None,
            "message": "Team belum digenerate oleh admin.",
        }

    members = await team_repo.get_members_by_version(team_version.id)
    my_member = next((m for m in members if m.player_id == player_id), None)
    if not my_member:
        return {
            "team_id": None,
            "team": None,
            "message": "Anda tidak dipilih dalam tim manapun.",
        }

    my_team_members = [m for m in members if m.team_id == my_member.team_id]
    team_player_ids = [m.player_id for m in my_team_members]
    team_participants = await participant_repo.get_by_ids(team_player_ids)
    participants_map = {p.id: p for p in team_participants}
    team_players = []
    for m in my_team_members:
        p = participants_map.get(m.player_id)
        if not p:
            continue
        import ast
        lane_caps = {}
        if p.lane_capabilities:
            try:
                lane_caps = ast.literal_eval(p.lane_capabilities)
            except Exception:
                lane_caps = {}
        team_players.append({
            "player_id": m.player_id,
            "name": p.name,
            "full_name": p.name,
            "email": p.email,
            "username": p.username,
            "assigned_lane": m.assigned_lane,
            "current_rank": p.current_rank,
            "current_stars": p.current_stars,
            "highest_rank": p.highest_rank,
            "highest_stars": p.highest_stars,
            "primary_lane": p.primary_lane,
            "secondary_lane": p.secondary_lane,
            "primary_lane_comfort": p.primary_lane_comfort or 0,
            "secondary_lane_comfort": p.secondary_lane_comfort or 0,
            "comfort_in_assigned_lane": m.comfort_in_assigned_lane or 0,
            "skill_score": p.skill_score or 0.0,
            "role_flexibility_score": p.role_flexibility_score or 0.0,
            "assignment_reason": m.assignment_reason,
            "role_compatibility_score": m.role_compatibility_score,
            "lane_capabilities": lane_caps,
            "skill_score_breakdown": _build_skill_breakdown(
                p.skill_score or 0.0,
                p.current_rank_score,
                p.current_star_score,
                p.highest_rank_score,
                p.highest_star_score,
            ),
            "role_flexibility_breakdown": _build_role_breakdown(p.primary_lane_comfort, p.secondary_lane_comfort),
            "fairness_breakdown": json.loads(m.fairness_breakdown) if m.fairness_breakdown else None,
        })

    sample_fairness = next((m for m in my_team_members if m.fairness_breakdown), None)
    fairness_breakdown = json.loads(sample_fairness.fairness_breakdown) if sample_fairness and sample_fairness.fairness_breakdown else None

    return {
        "team_id": my_member.team_id,
        "team": {
            "team_id": my_member.team_id,
            "players": team_players,
            "overall_fairness": my_member.overall_fairness,
            "average_skill_score": my_member.average_skill_score,
            "fairness_breakdown": fairness_breakdown,
        },
    }


@app.get("/api/config")
async def get_config():
    return JSONResponse(content={
        "default_random_seed": settings.default_random_seed,
        "current_rank_weight": settings.current_rank_weight,
        "current_star_weight": settings.current_star_weight,
        "highest_rank_weight": settings.highest_rank_weight,
        "highest_star_weight": settings.highest_star_weight,
    }, headers={"Cache-Control": "public, max-age=60"})


@app.get("/api/system-state", response_model=SystemStateResponse)
async def get_system_state(db: AsyncSession = Depends(get_db)):
    cached = cache.get("system_state")
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "public, max-age=10"})

    repo = SystemStateRepository(db)
    state = await repo.get_or_create()
    response = SystemStateResponse(
        state=state.state,
        current_ranking_version_id=state.current_ranking_version_id,
        current_team_version_id=state.current_team_version_id,
        updated_at=state.updated_at.isoformat() if state.updated_at else None,
    )
    cache.set("system_state", response.model_dump(), ttl_seconds=10)
    return JSONResponse(content=response.model_dump(), headers={"Cache-Control": "public, max-age=10"})


@app.post("/api/admin/generate-ranking")
async def admin_generate_ranking(request: AdminGenerateRankingRequest, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.ranking_repository import RankingRepository
    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.repositories.audit_repository import AuditRepository

    participant_repo = ParticipantRepository(db)
    ranking_repo = RankingRepository(db)
    system_state_repo = SystemStateRepository(db)
    audit_repo = AuditRepository(db)

    ranking_service = RankingService(
        participant_repo=participant_repo,
        ranking_repo=ranking_repo,
        system_state_repo=system_state_repo,
        audit_repo=audit_repo,
        payment_repo=PaymentRepository(db),
        team_service=service,
    )

    result = await ranking_service.generate_ranking(actor="admin")
    if not result.get("is_valid"):
        raise HTTPException(status_code=400, detail={
            "message": "Validasi data peserta gagal",
            "details": result,
        })

    return {
        "message": "Ranking berhasil digenerate",
        "ranking_version_id": result.get("ranking_version_id"),
        "total_participants": result.get("total"),
        "qualified_count": result.get("qualified_count"),
        "eliminated_count": result.get("eliminated_count"),
        "generated_at": result.get("generated_at"),
        "status": result.get("status"),
    }


@app.get("/api/admin/ranking-preview")
async def admin_ranking_preview(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    cached = cache.get("admin_ranking_preview")
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "public, max-age=10"})

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.ranking_repository import RankingRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.repositories.audit_repository import AuditRepository

    participant_repo = ParticipantRepository(db)
    ranking_repo = RankingRepository(db)
    system_state_repo = SystemStateRepository(db)
    audit_repo = AuditRepository(db)

    ranking_service = RankingService(
        participant_repo=participant_repo,
        ranking_repo=ranking_repo,
        system_state_repo=system_state_repo,
        audit_repo=audit_repo,
        payment_repo=PaymentRepository(db),
        team_service=service,
    )

    result = await ranking_service.generate_ranking(actor="admin")
    if not result.get("is_valid"):
        raise HTTPException(status_code=400, detail={
            "message": "Validasi data peserta gagal",
            "details": result,
        })

    cache.invalidate("admin_dashboard")
    cache.invalidate("admin_rankings")
    cache.invalidate("rankings_public")
    cache.invalidate("admin_ranking_versions")
    cache.invalidate("system_state")
    response = {
        "rankings": [r.dict() for r in result.get("rankings", [])],
        "total": result.get("total", 0),
        "qualified_count": result.get("qualified_count", 0),
        "eliminated_count": result.get("eliminated_count", 0),
        "score_components": result.get("score_components"),
        "preview_generated_at": result.get("generated_at"),
        "ranking_version_id": result.get("ranking_version_id"),
    }
    cache.set("admin_ranking_preview", response, ttl_seconds=10)
    return JSONResponse(content=response, headers={"Cache-Control": "public, max-age=10"})


@app.post("/api/admin/confirm-ranking")
async def admin_confirm_ranking(ranking_version_id: str = Query(...), x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.ranking_repository import RankingRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.repositories.audit_repository import AuditRepository

    participant_repo = ParticipantRepository(db)
    ranking_repo = RankingRepository(db)
    system_state_repo = SystemStateRepository(db)
    audit_repo = AuditRepository(db)

    ranking_service = RankingService(
        participant_repo=participant_repo,
        ranking_repo=ranking_repo,
        system_state_repo=system_state_repo,
        audit_repo=audit_repo,
        payment_repo=PaymentRepository(db),
        team_service=service,
    )

    result = await ranking_service.confirm_ranking(ranking_version_id, actor="admin")
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))

    cache.invalidate("admin_dashboard")
    cache.invalidate("admin_rankings")
    cache.invalidate("rankings_public")
    cache.invalidate("admin_ranking_versions")
    cache.invalidate("system_state")
    return result


@app.get("/api/admin/rankings")
async def admin_get_rankings(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db), page: int = 1, page_size: int = 9999):
    _require_admin(x_user_token)

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.ranking_repository import RankingRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.repositories.audit_repository import AuditRepository

    participant_repo = ParticipantRepository(db)
    ranking_repo = RankingRepository(db)
    system_state_repo = SystemStateRepository(db)
    audit_repo = AuditRepository(db)

    ranking_service = RankingService(
        participant_repo=participant_repo,
        ranking_repo=ranking_repo,
        system_state_repo=system_state_repo,
        audit_repo=audit_repo,
        payment_repo=PaymentRepository(db),
        team_service=service,
    )

    result = await ranking_service.get_rankings(page=page, page_size=page_size)
    return result


@app.get("/api/admin/ranking-versions")
async def admin_get_ranking_versions(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    cached = cache.get("admin_ranking_versions")
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "public, max-age=30"})

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.ranking_repository import RankingRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.repositories.audit_repository import AuditRepository

    participant_repo = ParticipantRepository(db)
    ranking_repo = RankingRepository(db)
    system_state_repo = SystemStateRepository(db)
    audit_repo = AuditRepository(db)

    ranking_service = RankingService(
        participant_repo=participant_repo,
        ranking_repo=ranking_repo,
        system_state_repo=system_state_repo,
        audit_repo=audit_repo,
        payment_repo=PaymentRepository(db),
        team_service=service,
    )

    versions = await ranking_service.get_ranking_versions()
    result = {"versions": versions}
    cache.set("admin_ranking_versions", result, ttl_seconds=30)
    return JSONResponse(content=result, headers={"Cache-Control": "public, max-age=30"})


@app.get("/api/admin/dashboard", response_model=AdminDashboardStats)
async def admin_dashboard(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    cached = cache.get("admin_dashboard")
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "public, max-age=15"})

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.ranking_repository import RankingRepository
    from app.repositories.team_repository import TeamRepository
    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.schemas.schemas import SystemState as SystemStateEnum

    from sqlalchemy import select, func, desc, case
    from app.models.models import Payment, ParticipantDB

    participant_repo = ParticipantRepository(db)
    ranking_repo = RankingRepository(db)
    team_repo = TeamRepository(db)
    payment_repo = PaymentRepository(db)
    system_state_repo = SystemStateRepository(db)

    participant_stats = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((ParticipantDB.skill_score.is_not(None), 1), else_=0)).label("processed"),
            func.sum(case((ParticipantDB.status == "QUALIFIED", 1), else_=0)).label("qualified"),
            func.sum(case((ParticipantDB.status == "ELIMINATED", 1), else_=0)).label("eliminated"),
        ).select_from(ParticipantDB)
    )
    stats_row = participant_stats.one_or_none()
    total_participants = stats_row.total or 0
    processed_participants = stats_row.processed or 0
    qualified_count = stats_row.qualified or 0
    eliminated_count = stats_row.eliminated or 0

    payment_stats = await db.execute(
        select(
            func.sum(case((Payment.status == "PENDING", 1), else_=0)).label("pending"),
            func.sum(case((Payment.status == "PAID", 1), else_=0)).label("paid"),
            func.sum(case((Payment.status == "FAILED", 1), else_=0)).label("failed"),
        ).select_from(Payment)
    )
    payment_row = payment_stats.one_or_none()
    payment_pending = payment_row.pending or 0
    payment_verified = payment_row.paid or 0
    payment_failed = payment_row.failed or 0

    active_ranking = await ranking_repo.get_active()
    ranking_generated = active_ranking is not None

    active_team = await team_repo.get_active()
    team_generated = active_team is not None
    total_teams = active_team.total_teams if active_team else 0

    state = await system_state_repo.get_or_create()

    result = AdminDashboardStats(
        total_participants=total_participants,
        processed_participants=processed_participants,
        qualified_count=qualified_count,
        eliminated_count=eliminated_count,
        teams_generated=team_generated,
        total_teams=total_teams,
        payment_pending_count=payment_pending,
        payment_verified_count=payment_verified,
        payment_failed_count=payment_failed,
        system_state=state.state,
        ranking_generated=ranking_generated,
        team_generated=team_generated,
    )
    cache.set("admin_dashboard", result.model_dump(), ttl_seconds=15)
    return JSONResponse(content=result.model_dump(), headers={"Cache-Control": "public, max-age=15"})


@app.post("/api/admin/generate-team")
async def admin_generate_team(request: AdminGenerateTeamRequest, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    try:
        _require_admin(x_user_token)

        from app.repositories.participant_repository import ParticipantRepository
        from app.repositories.ranking_repository import RankingRepository
        from app.repositories.team_repository import TeamRepository
        from app.repositories.system_state_repository import SystemStateRepository
        from app.repositories.audit_repository import AuditRepository
        from app.schemas.schemas import SystemState as SystemStateEnum

        participant_repo = ParticipantRepository(db)
        ranking_repo = RankingRepository(db)
        team_repo = TeamRepository(db)
        system_state_repo = SystemStateRepository(db)
        audit_repo = AuditRepository(db)

        active_ranking = await ranking_repo.get_active()
        if not active_ranking:
            raise HTTPException(status_code=400, detail="Belum ada ranking yang aktif. Generate ranking terlebih dahulu.")

        participants = await participant_repo.get_all()
        qualified = [p for p in participants if p.status == "QUALIFIED"]
        if not qualified:
            raise HTTPException(status_code=400, detail="Tidak ada peserta yang lolos kualifikasi.")

        payment_repo = PaymentRepository(db)
        qualified_ids = [p.id for p in qualified]
        payments = await payment_repo.get_by_player_ids(qualified_ids)
        paid_ids = {p.player_id for p in payments if p.status == "PAID"}
        unpaid = [p.name or p.id for p in qualified if p.id not in paid_ids]
        if unpaid:
            await audit_repo.create(
                action="TEAM_GENERATED_WITH_UNPAID",
                actor="admin",
                metadata={"unpaid": unpaid},
            )

        import json
        from app.schemas.schemas import ParticipantFeatures, TeamPlayer, TeamResult
        from app.models.models import TeamMember

        participant_features = []
        for p in qualified:
            lane_caps = {}
            if p.lane_capabilities:
                try:
                    lane_caps = ast.literal_eval(p.lane_capabilities)
                except Exception:
                    lane_caps = {}
            participant_features.append(ParticipantFeatures(
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
            ))

        seed = request.random_seed if request.random_seed is not None else 42
        num_teams = len(qualified) // 5

        from app.optimization.team_optimizer import TeamOptimizer
        from app.optimization.config.role_config import OptimizationConfig
        from app.optimization.history.history_manager import HistoryManager

        config = OptimizationConfig.get_default()
        history = HistoryManager(enable=config.enable_history)
        optimizer = TeamOptimizer(
            participants=participant_features,
            num_teams=num_teams,
            seed=seed,
            config=config,
            history=history,
        )

        try:
            # Run CPU-intensive optimization in a background thread to avoid blocking the event loop
            teams, iterations, fairness = await asyncio.to_thread(
                optimizer.optimize
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Gagal mengoptimalkan tim: {str(e)}")

        processing_time = 0.0

        await team_repo.deactivate_all()
        version_id = str(uuid4())
        team_version = await team_repo.create(
            version_id=version_id,
            ranking_version_id=active_ranking.id,
            total_teams=len(teams),
            total_participants=len(qualified),
            selected_count=len(qualified),
            not_selected_count=0,
            generated_by="admin",
            random_seed=seed,
            overall_fairness=round(fairness, 2),
            optimization_iterations=iterations,
            processing_time_ms=round(processing_time, 2),
        )

        members = []
        for team in teams:
            for player in team.players:
                members.append(TeamMember(
                    id=str(uuid4()),
                    team_version_id=version_id,
                    team_id=team.team_id,
                    player_id=player.player_id,
                    assigned_lane=player.assigned_lane,
                    comfort_in_assigned_lane=player.comfort_in_assigned_lane,
                    role_compatibility_score=player.role_compatibility_score,
                    assignment_reason=player.assignment_reason,
                    average_skill_score=team.average_skill_score,
                    role_balance_score=team.role_balance_score,
                    overall_fairness=team.overall_fairness,
                    fairness_breakdown=json.dumps(team.fairness_breakdown) if team.fairness_breakdown else None,
                ))
        await team_repo.bulk_add_members(members)

        await audit_repo.create(
            action="TEAM_GENERATED",
            actor="admin",
            metadata={
                "team_version_id": version_id,
                "total_teams": len(teams),
                "total_participants": len(qualified),
                "overall_fairness": round(fairness, 2),
            },
        )

        state = await system_state_repo.update_state(
            SystemStateEnum.team_generated.value,
            team_version_id=version_id,
        )

        cache.invalidate("admin_dashboard")
        cache.invalidate("admin_rankings")
        cache.invalidate("rankings_public")
        cache.invalidate("admin_ranking_versions")
        cache.invalidate("admin_team_versions")
        cache.invalidate("system_state")
        return {
            "message": "Tim berhasil digenerate",
            "team_version_id": version_id,
            "total_teams": len(teams),
            "total_participants": len(qualified),
            "overall_fairness": round(fairness, 2),
            "system_state": state.state,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gagal membuat tim: {str(e)}")


@app.get("/api/admin/team-versions")
async def admin_get_team_versions(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    cached = cache.get("admin_team_versions")
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "public, max-age=30"})

    team_repo = TeamRepository(db)
    versions = await team_repo.get_all()
    result = {
        "versions": [
            {
                "id": v.id,
                "ranking_version_id": v.ranking_version_id,
                "generated_at": v.generated_at.isoformat(),
                "confirmed_at": v.confirmed_at.isoformat() if v.confirmed_at else None,
                "status": v.status,
                "total_teams": v.total_teams,
                "total_participants": v.total_participants,
                "selected_count": v.selected_count,
                "not_selected_count": v.not_selected_count,
                "overall_fairness": v.overall_fairness,
                "random_seed": v.random_seed,
                "generated_by": v.generated_by,
                "is_active": v.is_active,
            }
            for v in versions
        ]
    }
    cache.set("admin_team_versions", result, ttl_seconds=30)
    return JSONResponse(content=result, headers={"Cache-Control": "public, max-age=30"})


@app.get("/api/admin/team-versions/{version_id}")
async def admin_get_team_version_detail(version_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.team_repository import TeamRepository
    from app.repositories.participant_repository import ParticipantRepository

    team_repo = TeamRepository(db)
    participant_repo = ParticipantRepository(db)

    version = await team_repo.get_by_id(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Team version not found")

    members = await team_repo.get_members_by_version(version_id)
    player_ids = [m.player_id for m in members if m.player_id]
    participants = await participant_repo.get_by_ids(player_ids)
    participants_map = {p.id: p for p in participants}

    members_with_details = []
    for m in members:
        p = participants_map.get(m.player_id)
        fairness_breakdown = None
        if m.fairness_breakdown:
            try:
                fairness_breakdown = json.loads(m.fairness_breakdown)
            except Exception:
                fairness_breakdown = None

        members_with_details.append({
            "id": m.id,
            "team_id": m.team_id,
            "player_id": m.player_id,
            "assigned_lane": m.assigned_lane,
            "comfort_in_assigned_lane": m.comfort_in_assigned_lane,
            "role_compatibility_score": m.role_compatibility_score,
            "assignment_reason": m.assignment_reason,
            "average_skill_score": m.average_skill_score,
            "role_balance_score": m.role_balance_score,
            "overall_fairness": m.overall_fairness,
            "fairness_breakdown": fairness_breakdown,
            "player_name": p.name if p else m.player_id,
            "player_email": p.email if p else "",
            "current_rank": p.current_rank if p else "",
            "current_stars": p.current_stars if p else 0,
            "highest_rank": p.highest_rank if p else "",
            "highest_stars": p.highest_stars if p else 0,
            "primary_lane": p.primary_lane if p else "",
            "secondary_lane": p.secondary_lane if p else "",
            "primary_lane_comfort": p.primary_lane_comfort if p else 0,
            "secondary_lane_comfort": p.secondary_lane_comfort if p else 0,
            "skill_score": p.skill_score if p else 0,
            "role_flexibility_score": p.role_flexibility_score if p else 0,
            "lane_capabilities": ast.literal_eval(p.lane_capabilities) if p and p.lane_capabilities else {},
            "status": p.status if p else "",
            "skill_score_breakdown": _build_skill_breakdown(
                p.skill_score if p else 0,
                p.current_rank_score if p else None,
                p.current_star_score if p else None,
                p.highest_rank_score if p else None,
                p.highest_star_score if p else None,
            ),
            "role_flexibility_breakdown": _build_role_breakdown(
                p.primary_lane_comfort if p else 0,
                p.secondary_lane_comfort if p else 0,
            ),
        })

    # Group members by team_id
    teams_map: Dict[str, list] = {}
    for m in members_with_details:
        teams_map.setdefault(m["team_id"], []).append(m)

    teams_response = []
    for team_id, players in sorted(teams_map.items()):
        sample_fairness = next((m["fairness_breakdown"] for m in players if m.get("fairness_breakdown")), None)
        teams_response.append({
            "team_id": team_id,
            "players": players,
            "overall_fairness": next((m["overall_fairness"] for m in players if m.get("overall_fairness") is not None), None),
            "fairness_breakdown": sample_fairness,
            "average_skill_score": next((m["average_skill_score"] for m in players if m.get("average_skill_score") is not None), None),
            "role_balance_score": next((m["role_balance_score"] for m in players if m.get("role_balance_score") is not None), None),
        })

    return {
        "id": version.id,
        "ranking_version_id": version.ranking_version_id,
        "total_teams": version.total_teams,
        "total_participants": version.total_participants,
        "selected_count": version.selected_count,
        "not_selected_count": version.not_selected_count,
        "overall_fairness": version.overall_fairness,
        "generated_at": version.generated_at.isoformat(),
        "status": version.status,
        "teams": teams_response,
    }


@app.post("/api/admin/verify-payment")
async def admin_verify_payment(request: PaymentVerificationRequest, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.audit_repository import AuditRepository

    payment_repo = PaymentRepository(db)
    audit_repo = AuditRepository(db)

    result = await payment_repo.verify(
        player_id=request.player_id,
        status=request.status,
        verified_by="admin",
        transaction_id=request.transaction_id,
        notes=request.notes,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Payment not found")

    cache.invalidate("admin_dashboard")
    cache.invalidate("admin_payments")
    cache.invalidate("admin_team_versions")
    cache.invalidate("rankings_public")
    cache.invalidate("system_state")
    return {
        "success": True,
        "id": result.id,
        "player_id": result.player_id,
        "status": result.status,
        "amount": result.amount,
        "paid_at": result.paid_at.isoformat() if result.paid_at else None,
        "verified_at": result.verified_at.isoformat() if result.verified_at else None,
        "verified_by": result.verified_by,
        "transaction_id": result.transaction_id,
        "notes": result.notes,
    }


@app.get("/api/admin/payments")
async def admin_get_payments(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db), page: int = 1, limit: int = 50):
    _require_admin(x_user_token)

    cached = cache.get(f"admin_payments_{page}_{limit}")
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "public, max-age=15"})

    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.participant_repository import ParticipantRepository
    from sqlalchemy import select, func, desc
    from app.models.models import Payment, ParticipantDB

    payment_repo = PaymentRepository(db)
    participant_repo = ParticipantRepository(db)

    offset = (page - 1) * limit

    total_result = await db.execute(select(func.count()).select_from(Payment))
    total_payments = total_result.scalar_one() or 0

    payments_result = await db.execute(
        select(Payment).order_by(desc(Payment.created_at)).limit(limit).offset(offset)
    )
    payments = list(payments_result.scalars().all())

    participant_ids = [p.player_id for p in payments if p.player_id]
    participants = await participant_repo.get_by_ids(participant_ids)
    participant_map = {p.id: p for p in participants}

    result = []
    for p in payments:
        participant = participant_map.get(p.player_id)
        result.append({
            "id": p.id,
            "player_id": p.player_id,
            "status": p.status,
            "amount": p.amount,
            "method": p.method,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "verified_by": p.verified_by,
            "verified_at": p.verified_at.isoformat() if p.verified_at else None,
            "transaction_id": p.transaction_id,
            "notes": p.notes,
            "created_at": p.created_at.isoformat(),
            "player_name": participant.name if participant else p.player_id,
            "player_email": participant.email if participant else "",
            "player_username": participant.username if participant else "",
            "current_rank": participant.current_rank if participant else "",
            "current_stars": participant.current_stars if participant else 0,
            "primary_lane": participant.primary_lane if participant else "",
        })

    response = {
        "payments": result,
        "total": total_payments,
        "page": page,
        "limit": limit,
        "total_pages": (total_payments + limit - 1) // limit,
    }
    cache.set(f"admin_payments_{page}_{limit}", response, ttl_seconds=15)
    return JSONResponse(content=response, headers={"Cache-Control": "public, max-age=15"})


@app.delete("/api/admin/payments/{payment_id}")
async def admin_delete_payment(payment_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.payment_repository import PaymentRepository
    payment_repo = PaymentRepository(db)
    success = await payment_repo.delete(payment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Payment not found")

    cache.invalidate("admin_dashboard")
    cache.invalidate("admin_payments")
    cache.invalidate("admin_team_versions")
    cache.invalidate("rankings_public")
    cache.invalidate("system_state")
    return {"success": True}


@app.get("/api/admin/audit-log")
async def admin_get_audit_log(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    cached = cache.get("admin_audit_log")
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "public, max-age=30"})

    from app.repositories.audit_repository import AuditRepository
    audit_repo = AuditRepository(db)
    logs = await audit_repo.get_all(limit=200)
    result = {
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "actor": log.actor,
                "timestamp": log.timestamp.isoformat(),
                "metadata": json.loads(log.log_metadata) if log.log_metadata else None,
            }
            for log in logs
        ]
    }
    cache.set("admin_audit_log", result, ttl_seconds=30)
    return JSONResponse(content=result, headers={"Cache-Control": "public, max-age=30"})


async def _maybe_regenerate_teams(db: AsyncSession, ranking_repo: RankingRepository, team_repo: TeamRepository,
                                 participant_repo: ParticipantRepository, payment_repo: PaymentRepository,
                                 system_state_repo: SystemStateRepository, audit_repo: AuditRepository) -> bool:
    qualified = await participant_repo.get_by_status("QUALIFIED")
    qualified_ids = [p.id for p in qualified]
    payments = await payment_repo.get_by_player_ids(qualified_ids)
    paid_ids = {p.player_id for p in payments if p.status == "PAID"}
    if not qualified_ids or not all(pid in paid_ids for pid in qualified_ids):
        return False

    active_ranking = await ranking_repo.get_active()
    if not active_ranking:
        return False

    participant_features = []
    for p in qualified:
        lane_caps = {}
        if p.lane_capabilities:
            try:
                lane_caps = ast.literal_eval(p.lane_capabilities)
            except Exception:
                lane_caps = {}
        participant_features.append(ParticipantFeatures(
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
        ))

    seed = 42
    num_teams = len(qualified) // 5

    from app.optimization.team_optimizer import TeamOptimizer
    from app.optimization.config.role_config import OptimizationConfig
    from app.optimization.history.history_manager import HistoryManager

    config = OptimizationConfig.get_default()
    history = HistoryManager(enable=config.enable_history)
    optimizer = TeamOptimizer(
        participants=participant_features,
        num_teams=num_teams,
        seed=seed,
        config=config,
        history=history,
    )

    teams, iterations, fairness = await asyncio.to_thread(optimizer.optimize)

    old_versions = await team_repo.get_all()
    for v in old_versions:
        v.is_active = False

    version_id = str(uuid4())
    version = TeamVersion(
        id=version_id,
        ranking_version_id=active_ranking.id,
        total_teams=len(teams),
        total_participants=len(qualified),
        selected_count=len(qualified),
        not_selected_count=0,
        overall_fairness=round(fairness, 2),
        random_seed=seed,
        optimization_iterations=iterations,
        processing_time_ms=0.0,
        generated_by="system",
        is_active=True,
        status="CONFIRMED",
    )
    db.add(version)
    await db.flush()

    for team_idx, team in enumerate(teams):
        team_id = f"T{team_idx + 1:02d}"
        for player in team:
            member = TeamMember(
                id=str(uuid4()),
                team_version_id=version_id,
                team_id=team_id,
                player_id=player.player_id,
                assigned_lane=player.primary_lane,
                comfort_in_assigned_lane=player.primary_lane_comfort,
                role_compatibility_score=0.0,
                assignment_reason="Auto-assigned after all payments completed",
                average_skill_score=0.0,
                role_balance_score=0.0,
                overall_fairness=0.0,
                fairness_breakdown=None,
            )
            db.add(member)

    await db.flush()

    await system_state_repo.update_state(
        SystemStateEnum.team_generated.value,
        team_version_id=version_id,
    )

    await audit_repo.create(
        action="TEAM_GENERATED",
        actor="system",
        metadata={
            "team_version_id": version_id,
            "total_teams": len(teams),
            "total_participants": len(qualified),
            "overall_fairness": round(fairness, 2),
            "auto_generated": True,
        },
    )

    cache.invalidate("admin_dashboard")
    cache.invalidate("admin_teams")
    cache.invalidate("teams_public")
    cache.invalidate("admin_team_versions")
    cache.invalidate("system_state")

    return True


@app.post("/api/admin/sync-participants")
async def admin_sync_participants(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    import csv
    import os
    import traceback
    from app.config.settings import settings
    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.team_repository import TeamRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.repositories.audit_repository import AuditRepository
    from app.models.models import Payment, TeamMember, ParticipantDB
    from app.schemas.schemas import SystemState as SystemStateEnum

    try:
        participant_repo = ParticipantRepository(db)
        payment_repo = PaymentRepository(db)
        team_repo = TeamRepository(db)
        system_state_repo = SystemStateRepository(db)
        audit_repo = AuditRepository(db)

        csv_path = settings.master_csv_path
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), csv_path)
        if not os.path.exists(csv_path):
            cwd = os.getcwd()
            alt_path = os.path.join(cwd, "backend", settings.master_csv_path)
            print(f"CSV not found at {csv_path}, trying {alt_path}, cwd={cwd}")
            if os.path.exists(alt_path):
                csv_path = alt_path
            else:
                raise HTTPException(status_code=404, detail=f"CSV file not found at {csv_path} or {alt_path}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_rows = list(reader)

        csv_emails = {row['Email Address'].strip().lower() for row in csv_rows if row['Email Address'].strip()}
        print(f"CSV loaded: {len(csv_rows)} rows, {len(csv_emails)} emails")

        current_participants = await participant_repo.get_all()
        to_delete = [p for p in current_participants if p.email and p.email.lower() not in csv_emails]
        delete_ids = [p.id for p in to_delete]
        print(f"Participants to delete: {len(delete_ids)}")

        if delete_ids:
            for pid in delete_ids:
                await db.execute(text("DELETE FROM payments WHERE player_id = :pid"), {"pid": pid})
                await db.execute(text("DELETE FROM team_members WHERE player_id = :pid"), {"pid": pid})
            placeholders = ",".join([f":pid{i}" for i in range(len(delete_ids))])
            params = {f"pid{i}": pid for i, pid in enumerate(delete_ids)}
            await db.execute(
                text(f"DELETE FROM participants WHERE id IN ({placeholders})"),
                params,
            )
            await audit_repo.create(
                action="PARTICIPANTS_DELETED",
                actor="admin",
                metadata={"deleted_count": len(delete_ids)},
            )

        existing = await participant_repo.get_all()
        existing_map = {p.email.lower(): p for p in existing if p.email}

        inserted = 0
        updated = 0
        for idx, row in enumerate(csv_rows):
            email = row['Email Address'].strip().lower()
            name = row['Nama Lengkap'].strip()
            username = row['Username Mobile Legends'].strip()
            current_rank = row['Rank Saat Ini '].strip()
            current_stars = int(row['Perolehan Bintang pada Rank Saat Ini']) if row['Perolehan Bintang pada Rank Saat Ini'].strip() else 0
            highest_rank = row['Rank Tertinggi '].strip()
            highest_stars = int(row['Perolehan Bintang pada Rank Tertinggi']) if row['Perolehan Bintang pada Rank Tertinggi'].strip() else 0
            primary_lane = row['Lane #1 Terbaik'].strip()
            primary_lane_comfort = int(row['Seberapa nyaman menggunakan Lane #1']) if row['Seberapa nyaman menggunakan Lane #1'].strip() else 0
            secondary_lane = row['Lane #2 Terbaik'].strip() if row['Lane #2 Terbaik'].strip() else None
            secondary_lane_comfort = int(row['Seberapa nyaman menggunakan Lane #2']) if row['Seberapa nyaman menggunakan Lane #2'].strip() else None

            if not email:
                continue

            expected_id = f"P{idx + 1:03d}"
            if email in existing_map:
                p = existing_map[email]
                p.name = name
                p.username = username
                p.current_rank = current_rank
                p.current_stars = current_stars
                p.highest_rank = highest_rank
                p.highest_stars = highest_stars
                p.primary_lane = primary_lane
                p.primary_lane_comfort = primary_lane_comfort
                p.secondary_lane = secondary_lane
                p.secondary_lane_comfort = secondary_lane_comfort
                p.status = "QUALIFIED"
                updated += 1
            else:
                new_p = ParticipantDB(
                    id=expected_id,
                    name=name,
                    email=email,
                    username=username,
                    current_rank=current_rank,
                    current_stars=current_stars,
                    highest_rank=highest_rank,
                    highest_stars=highest_stars,
                    primary_lane=primary_lane,
                    primary_lane_comfort=primary_lane_comfort,
                    secondary_lane=secondary_lane,
                    secondary_lane_comfort=secondary_lane_comfort,
                    status="QUALIFIED",
                )
                db.add(new_p)
                inserted += 1

        await db.flush()

        cache.invalidate("admin_dashboard")
        cache.invalidate("admin_rankings")
        cache.invalidate("rankings_public")
        cache.invalidate("admin_ranking_versions")
        cache.invalidate("admin_team_versions")
        cache.invalidate("system_state")

        # Auto-regenerate teams if all qualified participants have PAID payments
        qualified_after = await participant_repo.get_by_status("QUALIFIED")
        qualified_ids_after = [p.id for p in qualified_after]
        payments_after = await payment_repo.get_by_player_ids(qualified_ids_after)
        paid_ids_after = {p.player_id for p in payments_after if p.status == "PAID"}
        all_paid = len(qualified_ids_after) > 0 and all(pid in paid_ids_after for pid in qualified_ids_after)

        team_regenerated = False
        if all_paid:
            active_ranking = await ranking_repo.get_active()
            if active_ranking:
                participant_features = []
                for p in qualified_after:
                    lane_caps = {}
                    if p.lane_capabilities:
                        try:
                            lane_caps = ast.literal_eval(p.lane_capabilities)
                        except Exception:
                            lane_caps = {}
                    participant_features.append(ParticipantFeatures(
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
                    ))

                seed = 42
                num_teams = len(qualified_after) // 5

                from app.optimization.team_optimizer import TeamOptimizer
                from app.optimization.config.role_config import OptimizationConfig
                from app.optimization.history.history_manager import HistoryManager

                config = OptimizationConfig.get_default()
                history = HistoryManager(enable=config.enable_history)
                optimizer = TeamOptimizer(
                    participants=participant_features,
                    num_teams=num_teams,
                    seed=seed,
                    config=config,
                    history=history,
                )

                try:
                    teams, iterations, fairness = await asyncio.to_thread(optimizer.optimize)
                    
                    # Deactivate old team versions
                    old_versions = await team_repo.get_all()
                    for v in old_versions:
                        v.is_active = False
                    
                    # Create new team version
                    version_id = str(uuid4())
                    version = TeamVersion(
                        id=version_id,
                        ranking_version_id=active_ranking.id,
                        total_teams=len(teams),
                        total_participants=len(qualified_after),
                        selected_count=len(qualified_after),
                        not_selected_count=0,
                        overall_fairness=round(fairness, 2),
                        random_seed=seed,
                        optimization_iterations=iterations,
                        processing_time_ms=0.0,
                        generated_by="admin",
                        is_active=True,
                        status="CONFIRMED",
                    )
                    db.add(version)
                    await db.flush()

                    # Save team members
                    for team_idx, team in enumerate(teams):
                        team_id = f"T{team_idx + 1:02d}"
                        for player in team:
                            member = TeamMember(
                                id=str(uuid4()),
                                team_version_id=version_id,
                                team_id=team_id,
                                player_id=player.player_id,
                                assigned_lane=player.primary_lane,
                                comfort_in_assigned_lane=player.primary_lane_comfort,
                                role_compatibility_score=0.0,
                                assignment_reason="Auto-assigned after CSV sync",
                                average_skill_score=0.0,
                                role_balance_score=0.0,
                                overall_fairness=0.0,
                                fairness_breakdown=None,
                            )
                            db.add(member)

                    await db.flush()

                    # Update system state
                    await system_state_repo.update_state(
                        SystemStateEnum.team_generated.value,
                        team_version_id=version_id,
                    )

                    await audit_repo.create(
                        action="TEAM_GENERATED",
                        actor="admin",
                        metadata={
                            "team_version_id": version_id,
                            "total_teams": len(teams),
                            "total_participants": len(qualified_after),
                            "overall_fairness": round(fairness, 2),
                            "auto_generated": True,
                        },
                    )

                    team_regenerated = True
                except Exception as e:
                    print(f"Auto team regeneration failed: {e}")

        result = {
            "deleted_count": len(delete_ids),
            "inserted_count": inserted,
            "updated_count": updated,
            "total_participants": len(csv_emails),
            "team_regenerated": team_regenerated,
            "message": "Tim berhasil dibuat ulang secara otomatis." if team_regenerated else "Sinkronisasi peserta selesai. Tim akan dibuat ulang setelah semua peserta melakukan pembayaran.",
        }
        return result
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/api/admin/seed-payments")
async def admin_seed_payments(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.audit_repository import AuditRepository
    from datetime import datetime, timedelta

    participant_repo = ParticipantRepository(db)
    payment_repo = PaymentRepository(db)
    audit_repo = AuditRepository(db)

    qualified = await participant_repo.get_by_status("QUALIFIED")
    # Only auto-mark P001-P040 as PAID; P041-P045 must pay manually
    initial_batch = [p for p in qualified if p.id <= "P040"]
    existing = await payment_repo.get_by_player_ids([p.id for p in initial_batch])
    existing_ids = {p.player_id for p in existing}

    now = datetime.utcnow()
    inserted = 0
    for idx, p in enumerate(initial_batch, 1):
        if p.id in existing_ids:
            continue
        payment_id = f"PAY-{idx:03d}"
        transaction_id = f"TXN-{idx:08d}-{p.id[3:]}"
        await payment_repo.create_or_update(
            player_id=p.id,
            status="PAID",
            amount=20000.0,
            method="E-Money Dana/Link",
            paid_at=now - timedelta(days=7),
            verified_by="admin",
            verified_at=now - timedelta(days=3),
            transaction_id=transaction_id,
            notes="Auto-marked as PAID for initial batch",
        )
        inserted += 1

    if inserted > 0:
        await audit_repo.create(
            action="PAYMENTS_SEEDED",
            actor="admin",
            metadata={"inserted_count": inserted},
        )

    cache.invalidate("admin_dashboard")
    cache.invalidate("admin_payments")
    cache.invalidate("payments_public")
    cache.invalidate("rankings_public")

    return {"inserted_count": inserted, "total_qualified": len(qualified)}


@app.get("/api/me/payment")
async def get_my_payment(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_user(x_user_token)

    player_id = decode_token(x_user_token)["sub"]
    from app.repositories.payment_repository import PaymentRepository
    payment_repo = PaymentRepository(db)
    payment = await payment_repo.get_by_player_id(player_id)

    if not payment:
        return {
            "player_id": player_id,
            "status": "PENDING",
            "amount": None,
            "method": None,
            "paid_at": None,
            "verified_at": None,
            "verified_by": None,
            "transaction_id": None,
            "notes": None,
        }

    return {
        "id": payment.id,
        "player_id": payment.player_id,
        "status": payment.status,
        "amount": payment.amount,
        "method": payment.method,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "verified_at": payment.verified_at.isoformat() if payment.verified_at else None,
        "verified_by": payment.verified_by,
        "transaction_id": payment.transaction_id,
        "notes": payment.notes,
    }


@app.post("/api/me/submit-payment")
async def submit_payment(
    x_user_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    proof: UploadFile = File(...),
    notes: Optional[str] = Form(None),
):
    _require_user(x_user_token)

    player_id = decode_token(x_user_token)["sub"]
    content = await proof.read()
    storage_result = {}
    try:
        storage_result = await storage_service.upload_payment_proof(player_id, proof.filename, content)
    except Exception as e:
        print(f"Payment proof upload failed: {e}")

    from app.repositories.payment_repository import PaymentRepository
    payment_repo = PaymentRepository(db)
    payment = await payment_repo.create_or_update(
        player_id=player_id,
        status="PAID",
        amount=settings.payment_amount,
        method=settings.payment_method,
        notes=notes or f"Proof uploaded: {proof.filename}",
    )

    return {
        "success": True,
        "id": payment.id,
        "player_id": payment.player_id,
        "status": payment.status,
        "amount": payment.amount,
        "method": payment.method,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "verified_at": payment.verified_at.isoformat() if payment.verified_at else None,
        "verified_by": payment.verified_by,
        "transaction_id": payment.transaction_id,
        "notes": payment.notes,
        "proof_path": storage_result.get("path"),
    }


@app.get("/api/me/payment-status")
async def get_my_payment_status(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_user(x_user_token)

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.payment_repository import PaymentRepository
    participant_repo = ParticipantRepository(db)
    payment_repo = PaymentRepository(db)

    total_qualified = await participant_repo.count_by_status("QUALIFIED")
    paid_count = await payment_repo.count_by_status("PAID")

    all_paid = total_qualified > 0 and paid_count == total_qualified
    return {
        "total_qualified": total_qualified,
        "paid_count": paid_count,
        "pending_count": total_qualified - paid_count,
        "all_paid": all_paid,
        "payment_amount": settings.payment_amount,
        "payment_method": settings.payment_method,
        "payment_account_number": settings.payment_account_number,
        "payment_account_name": settings.payment_account_name,
    }


@app.get("/api/rankings")
async def get_all_rankings(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db), page: int = 1, page_size: int = 9999):
    _require_user(x_user_token)

    cache_key = f"rankings_public_{page}_{page_size}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JSONResponse(content=cached, headers={"Cache-Control": "public, max-age=30"})

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.ranking_repository import RankingRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.ranking_service import RankingService

    participant_repo = ParticipantRepository(db)
    ranking_repo = RankingRepository(db)
    system_state_repo = SystemStateRepository(db)
    audit_repo = AuditRepository(db)

    ranking_service = RankingService(
        participant_repo=participant_repo,
        ranking_repo=ranking_repo,
        system_state_repo=system_state_repo,
        audit_repo=audit_repo,
        payment_repo=PaymentRepository(db),
        team_service=service,
    )

    result = await ranking_service.get_rankings(page=page, page_size=page_size)
    current_player_id = decode_token(x_user_token)["sub"]
    current_role = decode_token(x_user_token).get("role", "user")
    result["current_user_id"] = current_player_id
    result["current_role"] = current_role

    cache.set(cache_key, result, ttl_seconds=30)
    return JSONResponse(content=result, headers={"Cache-Control": "public, max-age=30"})


@app.get("/api/teams")
async def get_all_teams(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_user(x_user_token)

    from app.repositories.team_repository import TeamRepository
    from app.repositories.participant_repository import ParticipantRepository
    team_repo = TeamRepository(db)
    participant_repo = ParticipantRepository(db)

    current_player_id = decode_token(x_user_token)["sub"]
    current_role = decode_token(x_user_token).get("role", "user")

    active = await team_repo.get_active()
    if not active:
        return {"teams": [], "current_user_id": current_player_id, "current_role": current_role, "all_paid": False}

    latest = active
    members = await team_repo.get_members_by_version(latest.id)
    player_ids = [m.player_id for m in members if m.player_id]
    participants = await participant_repo.get_by_ids(player_ids)
    participants_map = {p.id: p for p in participants}

    teams_map: Dict[str, list] = {}
    for m in members:
        p = participants_map.get(m.player_id)
        if not p:
            continue
        lane_caps = {}
        if p.lane_capabilities:
            try:
                lane_caps = ast.literal_eval(p.lane_capabilities)
            except Exception:
                lane_caps = {}
        teams_map.setdefault(m.team_id, []).append({
            "player_id": m.player_id,
            "assigned_lane": m.assigned_lane,
            "comfort_in_assigned_lane": m.comfort_in_assigned_lane or 0,
            "role_compatibility_score": m.role_compatibility_score,
            "assignment_reason": m.assignment_reason,
            "average_skill_score": m.average_skill_score,
            "role_balance_score": m.role_balance_score,
            "overall_fairness": m.overall_fairness,
            "fairness_breakdown": json.loads(m.fairness_breakdown) if m.fairness_breakdown else None,
            "player_name": p.name,
            "full_name": p.name,
            "email": p.email,
            "username": p.username,
            "current_rank": p.current_rank,
            "current_stars": p.current_stars,
            "highest_rank": p.highest_rank,
            "highest_stars": p.highest_stars,
            "primary_lane": p.primary_lane,
            "secondary_lane": p.secondary_lane,
            "primary_lane_comfort": p.primary_lane_comfort or 0,
            "secondary_lane_comfort": p.secondary_lane_comfort or 0,
            "skill_score": p.skill_score or 0.0,
            "role_flexibility_score": p.role_flexibility_score or 0.0,
            "lane_capabilities": lane_caps,
            "is_current_user": m.player_id == current_player_id,
            "skill_score_breakdown": _build_skill_breakdown(
                p.skill_score or 0.0,
                p.current_rank_score,
                p.current_star_score,
                p.highest_rank_score,
                p.highest_star_score,
            ),
            "role_flexibility_breakdown": _build_role_breakdown(p.primary_lane_comfort, p.secondary_lane_comfort),
        })

    teams_response = []
    for team_id, players in sorted(teams_map.items()):
        sample_fairness = next((p["fairness_breakdown"] for p in players if p.get("fairness_breakdown")), None)
        teams_response.append({
            "team_id": team_id,
            "players": players,
            "overall_fairness": next((p["overall_fairness"] for p in players if p.get("overall_fairness") is not None), None),
            "average_skill_score": next((p["average_skill_score"] for p in players if p.get("average_skill_score") is not None), None),
            "fairness_breakdown": sample_fairness,
        })

    from app.repositories.payment_repository import PaymentRepository
    payment_repo = PaymentRepository(db)
    total_qualified = await participant_repo.count_by_status("QUALIFIED")
    paid_count = await payment_repo.count_by_status("PAID")
    all_paid = total_qualified > 0 and paid_count == total_qualified

    return {
        "teams": teams_response,
        "current_user_id": current_player_id,
        "current_role": current_role,
        "all_paid": all_paid,
        "paid_count": paid_count,
        "total_qualified": total_qualified,
    }
