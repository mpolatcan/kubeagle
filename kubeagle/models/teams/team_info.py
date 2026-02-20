"""Team information models - consolidated from team_mapper.py and team_fetcher.py."""

from pydantic import BaseModel


class TeamInfo(BaseModel):
    """Represents a team from CODEOWNERS file."""

    name: str
    pattern: str
    owners: list[str]
    team_ref: str | None = None
