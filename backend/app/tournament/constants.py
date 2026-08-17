
class TournamentStatus(str):
    DRAFT = "DRAFT"
    CONFIGURED = "CONFIGURED"
    TEAMS_LOCKED = "TEAMS_LOCKED"
    GROUPS_CONFIGURED = "GROUPS_CONFIGURED"
    SCHEDULE_GENERATED = "SCHEDULE_GENERATED"
    GROUP_STAGE = "GROUP_STAGE"
    GROUP_FINALIZED = "GROUP_FINALIZED"
    KNOCKOUT = "KNOCKOUT"
    FINAL = "FINAL"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MatchStage(str):
    GROUP_STAGE = "GROUP_STAGE"
    KNOCKOUT = "KNOCKOUT"


class MatchStatus(str):
    SCHEDULED = "SCHEDULED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BracketType(str):
    UPPER = "UPPER"
    MIDDLE = "MIDDLE"
    LOWER = "LOWER"


class ThirdPlaceMode(str):
    DISABLED = "DISABLED"
    THIRD_PLACE_MATCH = "THIRD_PLACE_MATCH"
    BRACKET_BASED = "BRACKET_BASED"
    MANUAL = "MANUAL"


class BOFormat(str):
    BO1 = "BO1"
    BO3 = "BO3"
    BO5 = "BO5"
    BO7 = "BO7"


class BracketLoserRule(str):
    TO_MIDDLE = "TO_MIDDLE"
    TO_LOWER = "TO_LOWER"
    ELIMINATED = "ELIMINATED"


VALID_TRANSITIONS = {
    TournamentStatus.DRAFT: [TournamentStatus.CONFIGURED, TournamentStatus.GROUPS_CONFIGURED, TournamentStatus.CANCELLED],
    TournamentStatus.CONFIGURED: [TournamentStatus.TEAMS_LOCKED, TournamentStatus.DRAFT, TournamentStatus.GROUPS_CONFIGURED],
    TournamentStatus.TEAMS_LOCKED: [TournamentStatus.GROUPS_CONFIGURED, TournamentStatus.CONFIGURED],
    TournamentStatus.GROUPS_CONFIGURED: [TournamentStatus.SCHEDULE_GENERATED, TournamentStatus.TEAMS_LOCKED],
    TournamentStatus.SCHEDULE_GENERATED: [TournamentStatus.GROUP_STAGE, TournamentStatus.GROUPS_CONFIGURED],
    TournamentStatus.GROUP_STAGE: [TournamentStatus.GROUP_FINALIZED, TournamentStatus.SCHEDULE_GENERATED],
    TournamentStatus.GROUP_FINALIZED: [TournamentStatus.KNOCKOUT, TournamentStatus.GROUP_STAGE],
    TournamentStatus.KNOCKOUT: [TournamentStatus.FINAL, TournamentStatus.GROUP_FINALIZED],
    TournamentStatus.FINAL: [TournamentStatus.COMPLETED, TournamentStatus.KNOCKOUT],
    TournamentStatus.COMPLETED: [],
    TournamentStatus.CANCELLED: [],
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, [])


BO_WIN_REQUIREMENTS = {
    BOFormat.BO1: 1,
    BOFormat.BO3: 2,
    BOFormat.BO5: 3,
    BOFormat.BO7: 4,
}
