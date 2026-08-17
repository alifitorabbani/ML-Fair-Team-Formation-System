from typing import Optional, Dict, Any
import base64
import re

from app.tournament.constants import BOFormat, BO_WIN_REQUIREMENTS
from app.tournament.schemas.tournament_schemas import MatchResultOCRResponse


class OCRService:
    def __init__(self):
        pass

    def extract_result(self, image_bytes: bytes, match_format: str, team_a_id: Optional[str] = None, team_b_id: Optional[str] = None) -> Dict[str, Any]:
        required = BO_WIN_REQUIREMENTS.get(match_format, 1)
        text = self._mock_ocr(image_bytes)
        score_match = re.search(r"(\d+)\s*[-:]\s*(\d+)", text)
        if not score_match:
            return {
                "team_a_name": None,
                "team_b_name": None,
                "score_a": None,
                "score_b": None,
                "kills_a": None,
                "kills_b": None,
                "deaths_a": None,
                "deaths_b": None,
                "winner_team_id": None,
                "confidence": 0.0,
                "is_valid": False,
                "validation_message": "Could not detect score",
                "raw_text": text,
            }
        score_a = int(score_match.group(1))
        score_b = int(score_match.group(2))
        kills_match = re.search(r"(?:kill|kills?)\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
        deaths_match = re.search(r"(?:death|deaths?)\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
        kills_a = int(kills_match.group(1)) if kills_match else None
        deaths_a = None
        kills_b = None
        deaths_b = None
        if kills_a is not None:
            kills_b_match = re.search(r"(\d+)\s*(?:kills?|death|deaths?)", text[kills_match.end():], re.IGNORECASE)
            if kills_b_match:
                kills_b = int(kills_b_match.group(1))
        is_valid = True
        validation_message = "OK"
        confidence = 0.8
        if score_a != required and score_b != required:
            is_valid = False
            validation_message = f"Invalid score for {match_format}: winner must have {required} wins"
            confidence = 0.5
        elif abs(score_a - score_b) == 0:
            is_valid = False
            validation_message = "Score cannot be tied"
            confidence = 0.3
        else:
            winner_id = team_a_id if score_a > score_b else team_b_id
        return {
            "team_a_name": None,
            "team_b_name": None,
            "score_a": score_a,
            "score_b": score_b,
            "kills_a": kills_a,
            "kills_b": kills_b,
            "deaths_a": deaths_a,
            "deaths_b": deaths_b,
            "winner_team_id": team_a_id if score_a > score_b else team_b_id,
            "confidence": confidence,
            "is_valid": is_valid,
            "validation_message": validation_message,
            "raw_text": text,
        }

    def _mock_ocr(self, image_bytes: bytes) -> str:
        return "Team A 2 - 1 Team B\nKills: 15 - 12\nDeaths: 8 - 10"

    def validate_against_match(self, ocr_result: Dict[str, Any], team_a_id: Optional[str], team_b_id: Optional[str]) -> Dict[str, Any]:
        if not ocr_result.get("is_valid", False):
            return ocr_result
        score_a = ocr_result.get("score_a")
        score_b = ocr_result.get("score_b")
        if score_a is not None and score_b is not None:
            if team_a_id and team_b_id:
                ocr_result["winner_team_id"] = team_a_id if score_a > score_b else team_b_id
        return ocr_result
