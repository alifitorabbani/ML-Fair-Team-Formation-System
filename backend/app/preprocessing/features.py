import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from app.config.constants import Rank, RANK_SCORES, MAX_STARS_PER_RANK, normalize_rank
from app.config.settings import settings


def normalize_lane(lane_str: str) -> Optional[str]:
    if not lane_str or str(lane_str).strip() == "":
        return None
    cleaned = str(lane_str).strip().lower()
    mapping = {
        "jungle": "Jungle",
        "jungler": "Jungle",
        "exp": "EXP Lane",
        "exp lane": "EXP Lane",
        "exp_lane": "EXP Lane",
        "mid": "Mid Lane",
        "mid lane": "Mid Lane",
        "mid_lane": "Mid Lane",
        "gold": "Gold Lane",
        "gold lane": "Gold Lane",
        "gold_lane": "Gold Lane",
        "roam": "Roam",
        "roamer": "Roam",
        "support": "Roam",
    }
    return mapping.get(cleaned)


def safe_int(val, default=0) -> int:
    if pd.isna(val):
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0) -> float:
    if pd.isna(val):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def normalize_comfort(raw_comfort: int) -> float:
    if raw_comfort is None or raw_comfort == 0:
        return 0.0
    return float(6 - raw_comfort)


def normalize_star_score(rank: Rank, stars: int) -> float:
    max_stars = MAX_STARS_PER_RANK.get(rank, 100)
    if max_stars <= 0:
        return 0.0
    normalized = min(stars / max_stars, 1.0)
    return round(normalized * 100, 2)


def calculate_current_rank_score(rank: Rank) -> float:
    return RANK_SCORES.get(rank, 0.0)


def calculate_highest_rank_score(rank: Rank) -> float:
    return RANK_SCORES.get(rank, 0.0)


def calculate_skill_score(
    current_rank_score: float,
    current_star_score: float,
    highest_rank_score: float,
    highest_star_score: float,
) -> float:
    score = (
        settings.current_rank_weight * current_rank_score
        + settings.current_star_weight * current_star_score
        + settings.highest_rank_weight * highest_rank_score
        + settings.highest_star_weight * highest_star_score
    )
    return round(min(max(score, 0), 100), 2)


def calculate_role_flexibility_score(
    primary_comfort: int,
    secondary_comfort: int,
) -> float:
    primary_norm = normalize_comfort(primary_comfort) / 5.0
    if secondary_comfort is None or secondary_comfort == 0:
        return round(primary_norm * 100, 2)
    secondary_norm = normalize_comfort(secondary_comfort) / 5.0
    flexibility = (primary_norm * 0.7 + secondary_norm * 0.3)
    return round(flexibility * 100, 2)


def calculate_lane_comforts(
    primary_lane: str,
    secondary_lane: Optional[str],
    primary_comfort: int,
    secondary_comfort: Optional[int],
) -> Dict[str, float]:
    lanes = ["Jungle", "EXP Lane", "Mid Lane", "Gold Lane", "Roam"]
    comforts = {lane: 0.0 for lane in lanes}
    
    if primary_lane in comforts:
        comforts[primary_lane] = normalize_comfort(primary_comfort)
    
    if secondary_lane and secondary_lane in comforts and secondary_comfort is not None:
        comforts[secondary_lane] = max(comforts[secondary_lane], normalize_comfort(secondary_comfort))
    
    return comforts


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    
    result["current_rank_obj"] = result["Rank Saat Ini"].apply(lambda x: normalize_rank(str(x)) if pd.notna(x) else None)
    result["highest_rank_obj"] = result["Rank Tertinggi"].apply(lambda x: normalize_rank(str(x)) if pd.notna(x) else None)
    
    result["current_rank_score"] = result["current_rank_obj"].apply(lambda r: RANK_SCORES.get(r, 0.0) if r else 0.0)
    result["current_star_score"] = result.apply(lambda row: normalize_star_score(row["current_rank_obj"], safe_int(row["Perolehan Bintang pada Rank Saat Ini"])) if row["current_rank_obj"] else 0.0, axis=1)
    result["highest_rank_score"] = result["highest_rank_obj"].apply(lambda r: RANK_SCORES.get(r, 0.0) if r else 0.0)
    result["highest_star_score"] = result.apply(lambda row: normalize_star_score(row["highest_rank_obj"], safe_int(row["Perolehan Bintang pada Rank Tertinggi"])) if row["highest_rank_obj"] else 0.0, axis=1)
    
    result["Lane #1 Terbaik"] = result["Lane #1 Terbaik"].apply(lambda x: normalize_lane(str(x)) if pd.notna(x) else None)
    result["Lane #2 Terbaik"] = result["Lane #2 Terbaik"].apply(lambda x: normalize_lane(str(x)) if pd.notna(x) else None)
    
    result["skill_score"] = result.apply(
        lambda row: calculate_skill_score(
            row["current_rank_score"],
            row["current_star_score"],
            row["highest_rank_score"],
            row["highest_star_score"],
        ),
        axis=1,
    )
    
    result["role_flexibility_score"] = result.apply(
        lambda row: calculate_role_flexibility_score(
            safe_int(row["Seberapa nyaman menggunakan Lane #1"]),
            safe_int(row.get("Seberapa nyaman menggunakan Lane #2")),
        ),
        axis=1,
    )
    
    lane_comforts = result.apply(
        lambda row: calculate_lane_comforts(
            row["Lane #1 Terbaik"],
            row.get("Lane #2 Terbaik"),
            safe_int(row["Seberapa nyaman menggunakan Lane #1"]),
            safe_int(row.get("Seberapa nyaman menggunakan Lane #2")),
        ),
        axis=1,
    )
    
    result["jungle_comfort"] = lane_comforts.apply(lambda x: x.get("Jungle", 0.0))
    result["exp_comfort"] = lane_comforts.apply(lambda x: x.get("EXP Lane", 0.0))
    result["mid_comfort"] = lane_comforts.apply(lambda x: x.get("Mid Lane", 0.0))
    result["gold_comfort"] = lane_comforts.apply(lambda x: x.get("Gold Lane", 0.0))
    result["roam_comfort"] = lane_comforts.apply(lambda x: x.get("Roam", 0.0))
    
    result["lane_capabilities"] = lane_comforts.apply(lambda x: {k: v for k, v in x.items()})
    
    return result
