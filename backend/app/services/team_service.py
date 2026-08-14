import pandas as pd
from typing import List, Dict, Optional
from app.preprocessing.validation import validate_csv
from app.preprocessing.features import engineer_features, safe_int, safe_float, normalize_comfort
from app.schemas.schemas import (
    ParticipantFeatures,
    CSVValidationResult,
)
from app.config.settings import settings
from app.config.constants import Rank


class TeamFormationService:
    def __init__(self):
        self.raw_df: Optional[pd.DataFrame] = None
        self.participants: List[ParticipantFeatures] = []
        self.validation_result: Optional[CSVValidationResult] = None
        self.has_player_id_col: bool = False
        self.has_name_col: bool = False
        self.player_id_col: Optional[str] = None
        self.name_col: Optional[str] = None
        self.email_col: Optional[str] = None
        self.username_col: Optional[str] = None
    
    def validate_csv(self, df: pd.DataFrame) -> CSVValidationResult:
        result = validate_csv(df)
        
        missing_fields = [
            {"row": e["row"], "field": e["field"], "message": e["message"], "value": e.get("value")}
            for e in result["missing_fields"]
        ]
        invalid_records = [
            {"row": e["row"], "field": e["field"], "message": e["message"], "value": e.get("value")}
            for e in result["invalid_records"]
        ]
        duplicate_records = [
            {"row": e["row"], "field": e["field"], "message": e["message"], "value": e.get("value")}
            for e in result["duplicate_records"]
        ]
        
        self.has_player_id_col = result.get("has_player_id_col", False)
        self.has_name_col = result.get("has_name_col", False)
        self.player_id_col = result.get("player_id_col")
        self.name_col = result.get("name_col")
        self.email_col = result.get("email_col")
        self.username_col = result.get("username_col")
        
        self.validation_result = CSVValidationResult(
            total_rows=result["total_rows"],
            valid_participants=result["valid_participants"],
            invalid_participants=result["invalid_participants"],
            missing_fields=missing_fields,
            invalid_records=invalid_records,
            duplicate_records=duplicate_records,
            is_valid=result["column_valid"]
            and len(invalid_records) == 0
            and len(duplicate_records) == 0,
        )
        
        if result["valid_df"] is not None and len(result["valid_df"]) > 0:
            self.raw_df = result["valid_df"].copy()
        
        return self.validation_result
    
    def process_features(self) -> List[ParticipantFeatures]:
        if self.raw_df is None:
            raise ValueError("No valid data to process")
        
        df = engineer_features(self.raw_df)
        self.features_df = df
        
        participants = []
        player_id_col = self.player_id_col or "Player ID"
        name_col = self.name_col or "Name"
        email_col = self.email_col or "Email Address"
        username_col = self.username_col or "Username Mobile Legends"
        
        for idx, row in df.iterrows():
            raw_player_id = row.get(player_id_col) if player_id_col in row else None
            raw_name = row.get(name_col) if name_col in row else None
            raw_email = row.get(email_col) if email_col in row else None
            raw_username = row.get(username_col) if username_col in row else None
            
            if pd.notna(raw_player_id) and str(raw_player_id).strip():
                player_id = str(raw_player_id).strip()
            else:
                player_id = f"P{idx + 1:03d}"
            
            if pd.notna(raw_name) and str(raw_name).strip():
                name = str(raw_name).strip()
            else:
                name = None
            
            if pd.notna(raw_email) and str(raw_email).strip():
                email = str(raw_email).strip()
            else:
                email = None
            
            if pd.notna(raw_username) and str(raw_username).strip():
                username = str(raw_username).strip()
            else:
                username = None
            
            current_rank_obj = row.get("current_rank_obj")
            highest_rank_obj = row.get("highest_rank_obj")
            
            participant = ParticipantFeatures(
                player_id=player_id,
                name=name,
                full_name=name,
                email=email,
                username=username,
                current_rank=current_rank_obj.value if isinstance(current_rank_obj, Rank) else str(row.get("Rank Saat Ini", "")),
                current_stars=safe_int(row.get("Perolehan Bintang pada Rank Saat Ini")),
                highest_rank=highest_rank_obj.value if isinstance(highest_rank_obj, Rank) else str(row.get("Rank Tertinggi", "")),
                highest_stars=safe_int(row.get("Perolehan Bintang pada Rank Tertinggi")),
                current_rank_score=float(safe_float(row.get("current_rank_score", 0))),
                current_star_score=float(safe_float(row.get("current_star_score", 0))),
                highest_rank_score=float(safe_float(row.get("highest_rank_score", 0))),
                highest_star_score=float(safe_float(row.get("highest_star_score", 0))),
                primary_lane=row.get("Lane #1 Terbaik", ""),
                secondary_lane=row.get("Lane #2 Terbaik") if pd.notna(row.get("Lane #2 Terbaik")) else None,
                primary_lane_comfort=safe_int(row.get("Seberapa nyaman menggunakan Lane #1")),
                secondary_lane_comfort=safe_int(row.get("Seberapa nyaman menggunakan Lane #2")) if pd.notna(row.get("Seberapa nyaman menggunakan Lane #2")) else None,
                skill_score=float(safe_float(row.get("skill_score", 0))),
                skill_score_breakdown={
                    "current_rank_weight": settings.current_rank_weight,
                    "current_star_weight": settings.current_star_weight,
                    "highest_rank_weight": settings.highest_rank_weight,
                    "highest_star_weight": settings.highest_star_weight,
                    "current_rank_component": float(safe_float(row.get("current_rank_score", 0))) * settings.current_rank_weight,
                    "current_star_component": float(safe_float(row.get("current_star_score", 0))) * settings.current_star_weight,
                    "highest_rank_component": float(safe_float(row.get("highest_rank_score", 0))) * settings.highest_rank_weight,
                    "highest_star_component": float(safe_float(row.get("highest_star_score", 0))) * settings.highest_star_weight,
                },
                role_flexibility_score=float(safe_float(row.get("role_flexibility_score", 0))),
                role_flexibility_breakdown={
                    "primary_comfort": safe_int(row.get("Seberapa nyaman menggunakan Lane #1")),
                    "secondary_comfort": safe_int(row.get("Seberapa nyaman menggunakan Lane #2")) if pd.notna(row.get("Seberapa nyaman menggunakan Lane #2")) else None,
                    "normalized_primary": normalize_comfort(safe_int(row.get("Seberapa nyaman menggunakan Lane #1"))) / 5.0 * 100,
                },
                jungle_comfort=float(safe_float(row.get("jungle_comfort", 0))),
                exp_comfort=float(safe_float(row.get("exp_comfort", 0))),
                mid_comfort=float(safe_float(row.get("mid_comfort", 0))),
                gold_comfort=float(safe_float(row.get("gold_comfort", 0))),
                roam_comfort=float(safe_float(row.get("roam_comfort", 0))),
                lane_capabilities={
                    "Jungle": float(safe_float(row.get("jungle_comfort", 0))),
                    "EXP Lane": float(safe_float(row.get("exp_comfort", 0))),
                    "Mid Lane": float(safe_float(row.get("mid_comfort", 0))),
                    "Gold Lane": float(safe_float(row.get("gold_comfort", 0))),
                    "Roam": float(safe_float(row.get("roam_comfort", 0))),
                },
            )
            participants.append(participant)
        
        self.participants = participants
        return participants
