import pandas as pd
import re
import io
from typing import Dict, Optional, Tuple, List
from app.config.constants import Rank, RANK_ALIASES, RANK_SCORES, MAX_STARS_PER_RANK


def normalize_rank(rank_str: str) -> Optional[Rank]:
    if not rank_str or pd.isna(rank_str):
        return None
    cleaned = str(rank_str).strip().lower()
    if cleaned in RANK_ALIASES:
        return RANK_ALIASES[cleaned]
    return None


def normalize_lane(lane_str: str) -> Optional[str]:
    if not lane_str or pd.isna(lane_str):
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


def find_column(df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
    normalized_df_cols = {col.strip().lower(): col for col in df.columns}
    for name in possible_names:
        if name in normalized_df_cols:
            return normalized_df_cols[name]
    return None


COMFORT_LABELS = {
    1: "Sangat Nyaman",
    2: "Nyaman",
    3: "Cukup Nyaman",
    4: "Kurang Nyaman",
    5: "Tidak Nyaman",
}


def validate_csv_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    required_columns = [
        "Rank Saat Ini",
        "Perolehan Bintang pada Rank Saat Ini",
        "Rank Tertinggi",
        "Perolehan Bintang pada Rank Tertinggi",
        "Lane #1 Terbaik",
        "Seberapa nyaman menggunakan Lane #1",
        "Lane #2 Terbaik",
        "Seberapa nyaman menggunakan Lane #2",
    ]
    normalized_df_cols = {col.strip().lower(): col for col in df.columns}
    missing = []
    for req in required_columns:
        if req.strip().lower() not in normalized_df_cols:
            missing.append(req)
    return len(missing) == 0, missing


def validate_participant_row(row: pd.Series, row_index: int) -> List[Dict]:
    errors = []
    
    current_rank = normalize_rank(row.get("Rank Saat Ini"))
    if current_rank is None:
        errors.append({
            "row": row_index,
            "field": "Rank Saat Ini",
            "message": f"Nilai rank tidak valid: {row.get('Rank Saat Ini')}",
            "value": str(row.get("Rank Saat Ini"))
        })
    
    highest_rank = normalize_rank(row.get("Rank Tertinggi"))
    if highest_rank is None:
        errors.append({
            "row": row_index,
            "field": "Rank Tertinggi",
            "message": f"Nilai rank tidak valid: {row.get('Rank Tertinggi')}",
            "value": str(row.get("Rank Tertinggi"))
        })
    
    try:
        current_stars = int(float(row.get("Perolehan Bintang pada Rank Saat Ini", 0)))
        if current_stars < 0:
            errors.append({
                "row": row_index,
                "field": "Perolehan Bintang pada Rank Saat Ini",
                "message": "Nilai bintang tidak boleh negatif",
                "value": str(current_stars)
            })
    except (ValueError, TypeError):
        errors.append({
            "row": row_index,
            "field": "Perolehan Bintang pada Rank Saat Ini",
            "message": "Nilai bintang tidak valid",
            "value": str(row.get("Perolehan Bintang pada Rank Saat Ini"))
        })
    
    try:
        highest_stars = int(float(row.get("Perolehan Bintang pada Rank Tertinggi", 0)))
        if highest_stars < 0:
            errors.append({
                "row": row_index,
                "field": "Perolehan Bintang pada Rank Tertinggi",
                "message": "Nilai bintang tidak boleh negatif",
                "value": str(highest_stars)
            })
    except (ValueError, TypeError):
        errors.append({
            "row": row_index,
            "field": "Perolehan Bintang pada Rank Tertinggi",
            "message": "Nilai bintang tidak valid",
            "value": str(row.get("Perolehan Bintang pada Rank Tertinggi"))
        })
    
    primary_lane = normalize_lane(row.get("Lane #1 Terbaik"))
    if primary_lane is None:
        errors.append({
            "row": row_index,
            "field": "Lane #1 Terbaik",
            "message": f"Nilai lane tidak valid: {row.get('Lane #1 Terbaik')}",
            "value": str(row.get("Lane #1 Terbaik"))
        })
    
    try:
        p_comfort = int(float(row.get("Seberapa nyaman menggunakan Lane #1", 0)))
        if not (1 <= p_comfort <= 5):
            errors.append({
                "row": row_index,
                "field": "Seberapa nyaman menggunakan Lane #1",
                "message": "Nilai kenyamanan harus antara 1 dan 5",
                "value": str(p_comfort)
            })
    except (ValueError, TypeError):
        errors.append({
            "row": row_index,
            "field": "Seberapa nyaman menggunakan Lane #1",
            "message": "Nilai kenyamanan tidak valid",
            "value": str(row.get("Seberapa nyaman menggunakan Lane #1"))
        })
    
    secondary_lane_raw = row.get("Lane #2 Terbaik")
    if pd.notna(secondary_lane_raw) and str(secondary_lane_raw).strip():
        secondary_lane = normalize_lane(secondary_lane_raw)
        if secondary_lane is None:
            errors.append({
                "row": row_index,
                "field": "Lane #2 Terbaik",
                "message": f"Nilai lane tidak valid: {secondary_lane_raw}",
                "value": str(secondary_lane_raw)
            })
        else:
            try:
                s_comfort = int(float(row.get("Seberapa nyaman menggunakan Lane #2", 0)))
                if not (1 <= s_comfort <= 5):
                    errors.append({
                        "row": row_index,
                        "field": "Seberapa nyaman menggunakan Lane #2",
                        "message": "Nilai kenyamanan harus antara 1 dan 5",
                        "value": str(s_comfort)
                    })
            except (ValueError, TypeError):
                errors.append({
                    "row": row_index,
                    "field": "Seberapa nyaman menggunakan Lane #2",
                    "message": "Nilai kenyamanan tidak valid",
                    "value": str(row.get("Seberapa nyaman menggunakan Lane #2"))
                })
    
    return errors


def validate_csv(df: pd.DataFrame) -> Dict:
    df = df.rename(columns=lambda x: x.strip() if isinstance(x, str) else x)
    column_valid, missing_cols = validate_csv_columns(df)
    
    missing_fields = []
    invalid_records = []
    duplicates = []
    
    seen_ids = set()
    seen_names = set()
    
    valid_rows = []
    
    has_player_id_col = "Player ID" in df.columns
    player_id_col = find_column(df, ["player id", "player_id", "id", "participant id"])
    name_col = find_column(df, ["name", "nama", "nama lengkap", "full name", "full_name"])
    email_col = find_column(df, ["email address", "email", "e-mail", "email address"])
    username_col = find_column(df, ["username mobile legends", "username", "user name", "ml username"])
    has_name_col = name_col is not None
    
    if not has_player_id_col:
        missing_fields.append({
            "row": 0,
            "field": player_id_col or "Player ID",
            "message": f"Kolom '{player_id_col or 'Player ID'}' tidak ditemukan. ID akan dibuat otomatis.",
            "value": None
        })
    
    if not has_name_col:
        missing_fields.append({
            "row": 0,
            "field": name_col or "Name",
            "message": f"Kolom '{name_col or 'Name'}' tidak ditemukan. Nama akan dikosongkan.",
            "value": None
        })
    
    if not column_valid:
        detected = ", ".join(df.columns.tolist())
        missing_fields.append({
            "row": 0,
            "field": "Kolom Wajib",
            "message": f"Kolom yang dibutuhkan tidak ditemukan: {', '.join(missing_cols)}. Kolom yang terdeteksi: [{detected}]",
            "value": None
        })
        return {
            "total_rows": len(df),
            "valid_participants": 0,
            "invalid_participants": len(df),
            "missing_fields": missing_fields,
            "invalid_records": [],
            "duplicate_records": [],
            "valid_df": pd.DataFrame(),
            "column_valid": False,
            "missing_columns": missing_cols,
            "has_player_id_col": has_player_id_col,
            "has_name_col": has_name_col,
        }
    
    for idx, row in df.iterrows():
        row_num = idx + 2
        
        rank_value = row.get("Rank Saat Ini")
        lane_value = row.get("Lane #1 Terbaik")
        
        empty_fields = []
        if pd.isna(rank_value) or str(rank_value).strip() == "":
            empty_fields.append("Rank Saat Ini")
        if pd.isna(lane_value) or str(lane_value).strip() == "":
            empty_fields.append("Lane #1 Terbaik")
        
        if empty_fields:
            missing_fields.append({
                "row": row_num,
                "field": "required",
                "message": f"Field wajib kosong: {', '.join(empty_fields)}",
                "value": None
            })
            invalid_records.append({
                "row": row_num,
                "field": "required",
                "message": f"Field wajib kosong: {', '.join(empty_fields)}",
                "value": None
            })
            continue
        
        errors = validate_participant_row(row, row_num)
        if errors:
            invalid_records.extend(errors)
            continue
        
        current_rank_obj = row.get("current_rank_obj")
        highest_rank_obj = row.get("highest_rank_obj")
        if current_rank_obj is not None and highest_rank_obj is not None:
            rank_order = {
                "Warrior": 1, "Elite": 2, "Master": 3, "Grandmaster": 4,
                "Epic": 5, "Legend": 6, "Mythic": 7,
                "Mythical Honor": 8, "Mythical Glory": 9, "Mythical Immortal": 10,
            }
            current_val = rank_order.get(str(current_rank_obj), 0)
            highest_val = rank_order.get(str(highest_rank_obj), 0)
            if highest_val < current_val:
                invalid_records.append({
                    "row": row_num,
                    "field": "Rank Tertinggi",
                    "message": "Rank tertinggi tidak boleh lebih rendah dari rank saat ini",
                    "value": str(highest_rank_obj),
                })
                continue
        
        valid_rows.append(idx)
    
    for idx in df.index:
        row_num = idx + 2
        
        if has_player_id_col:
            raw_id = str(df.at[idx, player_id_col]) if pd.notna(df.at[idx, player_id_col]) else None
            if raw_id and raw_id.strip():
                if raw_id in seen_ids:
                    duplicates.append({
                        "row": row_num,
                        "field": "Player ID",
                        "message": f"Duplicate Player ID detected at row {row_num}",
                        "value": raw_id
                    })
                seen_ids.add(raw_id)
        
        if has_name_col:
            raw_name = str(df.at[idx, name_col]) if pd.notna(df.at[idx, name_col]) else None
            if raw_name and raw_name.strip():
                if raw_name in seen_names:
                    duplicates.append({
                        "row": row_num,
                        "field": "Name",
                        "message": f"Duplicate Name detected at row {row_num}",
                        "value": raw_name
                    })
                seen_names.add(raw_name)
    
    valid_df = df.iloc[valid_rows].copy() if valid_rows else pd.DataFrame()
    
    return {
        "total_rows": len(df),
        "valid_participants": len(valid_rows),
        "invalid_participants": len(df) - len(valid_rows),
        "missing_fields": missing_fields,
        "invalid_records": invalid_records,
        "duplicate_records": duplicates,
        "valid_df": valid_df,
        "column_valid": column_valid,
        "missing_columns": missing_cols,
        "has_player_id_col": has_player_id_col,
        "has_name_col": has_name_col,
        "player_id_col": player_id_col,
        "name_col": name_col,
        "email_col": email_col,
        "username_col": username_col,
    }
