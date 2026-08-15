from fastapi import FastAPI, HTTPException, Depends, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
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
    cr = current_rank_score if current_rank_score is not None else total * settings.current_rank_weight
    cs = current_star_score if current_star_score is not None else total * settings.current_star_weight
    hr = highest_rank_score if highest_rank_score is not None else total * settings.highest_rank_weight
    hs = highest_star_score if highest_star_score is not None else total * settings.highest_star_weight

    raw_total = cr + cs + hr + hs
    components = {
        "current_rank": {
            "raw_score": round(cr, 4),
            "weight": settings.current_rank_weight,
            "weight_percent": round(settings.current_rank_weight * 100, 2),
            "contribution": round(cr, 4),
            "formula": f"{round(cr, 4)} × {settings.current_rank_weight} = {round(cr * settings.current_rank_weight, 4)}",
        },
        "current_star": {
            "raw_score": round(cs, 4),
            "weight": settings.current_star_weight,
            "weight_percent": round(settings.current_star_weight * 100, 2),
            "contribution": round(cs, 4),
            "formula": f"{round(cs, 4)} × {settings.current_star_weight} = {round(cs * settings.current_star_weight, 4)}",
        },
        "highest_rank": {
            "raw_score": round(hr, 4),
            "weight": settings.highest_rank_weight,
            "weight_percent": round(settings.highest_rank_weight * 100, 2),
            "contribution": round(hr, 4),
            "formula": f"{round(hr, 4)} × {settings.highest_rank_weight} = {round(hr * settings.highest_rank_weight, 4)}",
        },
        "highest_star": {
            "raw_score": round(hs, 4),
            "weight": settings.highest_star_weight,
            "weight_percent": round(settings.highest_star_weight * 100, 2),
            "contribution": round(hs, 4),
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


def _build_role_breakdown(primary_lane_comfort: Optional[int], secondary_lane_comfort: Optional[int]) -> Optional[Dict[str, Any]]:
    primary = primary_lane_comfort or 0
    secondary = secondary_lane_comfort or 0
    if primary == 0 and secondary == 0:
        return None

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
    except Exception as e:
        print(f"Startup warning: database initialization failed: {e}")
    yield


app = FastAPI(
    title="ML Fair Team Formation System",
    description="API for fair Mobile Legends team formation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        await repo.upsert_many(participant_dicts)
        await db.commit()
        count = len(await repo.get_all())
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
            "message": "Pembayaran belum diverifikasi. Tim belum dapat dilihat.",
        }

    participant_repo = ParticipantRepository(db)
    qualified = [p for p in await participant_repo.get_all() if p.status == "QUALIFIED"]
    unpaid = []
    for p in qualified:
        pay = await payment_repo.get_by_player_id(p.id)
        if not pay or pay.status != "PAID":
            unpaid.append(p.name or p.id)
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
    team_players = []
    for m in my_team_members:
        p = await repo.get_by_id(m.player_id)
        if p:
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
    return {
        "default_random_seed": settings.default_random_seed,
        "current_rank_weight": settings.current_rank_weight,
        "current_star_weight": settings.current_star_weight,
        "highest_rank_weight": settings.highest_rank_weight,
        "highest_star_weight": settings.highest_star_weight,
    }


@app.get("/api/system-state", response_model=SystemStateResponse)
async def get_system_state(db: AsyncSession = Depends(get_db)):
    repo = SystemStateRepository(db)
    state = await repo.get_or_create()
    return SystemStateResponse(
        state=state.state,
        current_ranking_version_id=state.current_ranking_version_id,
        current_team_version_id=state.current_team_version_id,
        updated_at=state.updated_at.isoformat() if state.updated_at else None,
    )


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

    return {
        "rankings": [r.dict() for r in result.get("rankings", [])],
        "total": result.get("total", 0),
        "qualified_count": result.get("qualified_count", 0),
        "eliminated_count": result.get("eliminated_count", 0),
        "score_components": result.get("score_components"),
        "preview_generated_at": result.get("generated_at"),
        "ranking_version_id": result.get("ranking_version_id"),
    }


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

    return result


@app.get("/api/admin/rankings")
async def admin_get_rankings(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
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

    result = await ranking_service.get_rankings()
    return result


@app.get("/api/admin/ranking-versions")
async def admin_get_ranking_versions(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
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

    versions = await ranking_service.get_ranking_versions()
    return {"versions": versions}


@app.get("/api/admin/dashboard", response_model=AdminDashboardStats)
async def admin_dashboard(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.ranking_repository import RankingRepository
    from app.repositories.team_repository import TeamRepository
    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.system_state_repository import SystemStateRepository
    from app.schemas.schemas import SystemState as SystemStateEnum

    participant_repo = ParticipantRepository(db)
    ranking_repo = RankingRepository(db)
    team_repo = TeamRepository(db)
    payment_repo = PaymentRepository(db)
    system_state_repo = SystemStateRepository(db)

    all_participants = await participant_repo.get_all()
    total_participants = len(all_participants)
    processed_participants = sum(1 for p in all_participants if p.skill_score is not None)
    qualified_count = sum(1 for p in all_participants if p.status == "QUALIFIED")
    eliminated_count = sum(1 for p in all_participants if p.status == "ELIMINATED")

    active_ranking = await ranking_repo.get_active()
    ranking_generated = active_ranking is not None

    active_team = await team_repo.get_active()
    team_generated = active_team is not None
    total_teams = active_team.total_teams if active_team else 0

    payment_stats = await PaymentRepository(db).get_all()
    payment_pending = sum(1 for p in payment_stats if p.status == "PENDING")
    payment_verified = sum(1 for p in payment_stats if p.status == "PAID")
    payment_failed = sum(1 for p in payment_stats if p.status == "FAILED")

    state = await system_state_repo.get_or_create()

    return AdminDashboardStats(
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
        unpaid = []
        for p in qualified:
            payment = await payment_repo.get_by_player_id(p.id)
            if not payment or payment.status != "PAID":
                unpaid.append(p.name or p.id)
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

    team_repo = TeamRepository(db)
    versions = await team_repo.get_all()
    return {
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
    members_with_details = []
    for m in members:
        p = await participant_repo.get_by_id(m.player_id)
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
async def admin_get_payments(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.participant_repository import ParticipantRepository
    payment_repo = PaymentRepository(db)
    participant_repo = ParticipantRepository(db)
    payments = await payment_repo.get_all()
    participants = await participant_repo.get_all()
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
    return {
        "payments": result
    }


@app.delete("/api/admin/payments/{payment_id}")
async def admin_delete_payment(payment_id: str, x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.payment_repository import PaymentRepository
    payment_repo = PaymentRepository(db)
    success = await payment_repo.delete(payment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {"success": True}


@app.get("/api/admin/audit-log")
async def admin_get_audit_log(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_admin(x_user_token)

    from app.repositories.audit_repository import AuditRepository
    audit_repo = AuditRepository(db)
    logs = await audit_repo.get_all(limit=200)
    return {
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
    storage_result = await storage_service.upload_payment_proof(player_id, proof.filename, content)

    from app.repositories.payment_repository import PaymentRepository
    payment_repo = PaymentRepository(db)
    payment = await payment_repo.create_or_update(
        player_id=player_id,
        status="PENDING",
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

    qualified = [p for p in await participant_repo.get_all() if p.status == "QUALIFIED"]
    total_qualified = len(qualified)
    paid_count = 0
    for p in qualified:
        payment = await payment_repo.get_by_player_id(p.id)
        if payment and payment.status == "PAID":
            paid_count += 1

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
async def get_all_rankings(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_user(x_user_token)

    from app.repositories.participant_repository import ParticipantRepository
    participant_repo = ParticipantRepository(db)
    participants = await participant_repo.get_all()
    qualified = [p for p in participants if p.status == "QUALIFIED"]
    qualified.sort(key=lambda p: (p.rank if p.rank else 9999))

    current_player_id = decode_token(x_user_token)["sub"]
    current_role = decode_token(x_user_token).get("role", "user")

    rankings = []
    for idx, p in enumerate(qualified, start=1):
        lane_caps = {}
        if p.lane_capabilities:
            try:
                lane_caps = ast.literal_eval(p.lane_capabilities)
            except Exception:
                lane_caps = {}
        rankings.append({
            "rank": idx,
            "player_id": p.id,
            "full_name": p.name,
            "name": p.name,
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
            "status": p.status,
            "is_current_user": p.id == current_player_id,
            "current_role": current_role,
            "skill_score_breakdown": _build_skill_breakdown(
                p.skill_score or 0.0,
                p.current_rank_score,
                p.current_star_score,
                p.highest_rank_score,
                p.highest_star_score,
            ),
            "role_flexibility_breakdown": _build_role_breakdown(p.primary_lane_comfort, p.secondary_lane_comfort),
        })

    return {
        "rankings": rankings,
        "total": len(rankings),
        "current_user_id": current_player_id,
        "current_role": current_role,
    }


@app.get("/api/teams")
async def get_all_teams(x_user_token: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    _require_user(x_user_token)

    from app.repositories.team_repository import TeamRepository
    from app.repositories.participant_repository import ParticipantRepository
    team_repo = TeamRepository(db)
    participant_repo = ParticipantRepository(db)

    current_player_id = decode_token(x_user_token)["sub"]
    current_role = decode_token(x_user_token).get("role", "user")

    versions = await team_repo.get_all()
    active = [v for v in versions if v.is_active]
    if not active:
        return {"teams": [], "current_user_id": current_player_id, "current_role": current_role, "all_paid": False}

    latest = sorted(active, key=lambda v: v.generated_at, reverse=True)[0]
    members = await team_repo.get_members_by_version(latest.id)
    participants_map = {p.id: p for p in await participant_repo.get_all()}

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
    qualified = [p for p in await participant_repo.get_all() if p.status == "QUALIFIED"]
    paid_count = 0
    for p in qualified:
        payment = await payment_repo.get_by_player_id(p.id)
        if payment and payment.status == "PAID":
            paid_count += 1
    all_paid = len(qualified) > 0 and paid_count == len(qualified)

    return {
        "teams": teams_response,
        "current_user_id": current_player_id,
        "current_role": current_role,
        "all_paid": all_paid,
        "paid_count": paid_count,
        "total_qualified": len(qualified),
    }
