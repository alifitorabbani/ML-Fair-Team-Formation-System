from enum import Enum
from typing import Optional


class Rank(str, Enum):
    warrior = "Warrior"
    elite = "Elite"
    master = "Master"
    grandmaster = "Grandmaster"
    epic = "Epic"
    legend = "Legend"
    mythic = "Mythic"
    mythical_honor = "Mythical Honor"
    mythical_glory = "Mythical Glory"
    mythical_immortal = "Mythical Immortal"


RANK_SCORES = {
    Rank.warrior: 10.0,
    Rank.elite: 20.0,
    Rank.master: 30.0,
    Rank.grandmaster: 40.0,
    Rank.epic: 50.0,
    Rank.legend: 60.0,
    Rank.mythic: 70.0,
    Rank.mythical_honor: 80.0,
    Rank.mythical_glory: 90.0,
    Rank.mythical_immortal: 100.0,
}

MAX_STARS_PER_RANK = {
    Rank.warrior: 10,
    Rank.elite: 10,
    Rank.master: 10,
    Rank.grandmaster: 10,
    Rank.epic: 10,
    Rank.legend: 10,
    Rank.mythic: 25,
    Rank.mythical_honor: 100,
    Rank.mythical_glory: 100,
    Rank.mythical_immortal: 100,
}

RANK_ALIASES = {
    "warrior": Rank.warrior,
    "elite": Rank.elite,
    "master": Rank.master,
    "grandmaster": Rank.grandmaster,
    "grand master": Rank.grandmaster,
    "epic": Rank.epic,
    "legend": Rank.legend,
    "mythic": Rank.mythic,
    "mythical honor": Rank.mythical_honor,
    "mythical honour": Rank.mythical_honor,
    "mythical glory": Rank.mythical_glory,
    "mythical immortal": Rank.mythical_immortal,
    "mythic honor": Rank.mythical_honor,
    "mythic glory": Rank.mythical_glory,
    "mythic immortal": Rank.mythical_immortal,
}


def normalize_rank(rank_str: str) -> Optional[Rank]:
    if not rank_str or rank_str.strip() == "":
        return None
    cleaned = str(rank_str).strip().lower()
    if cleaned in RANK_ALIASES:
        return RANK_ALIASES[cleaned]
    return None
