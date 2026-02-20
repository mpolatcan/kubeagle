"""Team fetcher for team controller - fetches team data from CODEOWNERS file."""

from __future__ import annotations

from pathlib import Path

from kubeagle.constants.patterns import (
    EMAIL_TEAM_PATTERN,
    GITHUB_TEAM_PATTERN,
    TEAM_PATTERN,
)
from kubeagle.models.teams.team_info import TeamInfo


class TeamFetcher:
    """Fetches team data from CODEOWNERS file."""

    def __init__(self, codeowners_path: Path | None = None) -> None:
        """Initialize team fetcher.

        Args:
            codeowners_path: Optional path to CODEOWNERS file.
        """
        self.codeowners_path = codeowners_path
        self.teams: list[TeamInfo] = []
        self.team_mapping: dict[str, str] = {}

    def load_codeowners(self, codeowners_path: Path) -> None:
        """Load and parse a CODEOWNERS file.

        Args:
            codeowners_path: Path to CODEOWNERS file.
        """
        self.teams = []
        self.team_mapping = {}
        self._parse_codeowners(codeowners_path)

    def _parse_codeowners(self, path: Path) -> None:
        """Parse CODEOWNERS file to extract team mappings.

        Args:
            path: Path to CODEOWNERS file.
        """
        if not path.exists():
            return

        try:
            with open(path, encoding="utf-8") as f:
                current_team = "Unknown"
                current_team_ref: str | None = None
                current_owners: list[str] = []

                for raw_line in f:
                    line = raw_line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Handle team header comments
                    if line.startswith("#"):
                        # Check for team separator (======)
                        if "=======" in line:
                            continue

                        # Look for team name in comment using TEAM_PATTERN
                        match = TEAM_PATTERN.search(line)
                        if match:
                            team_name = match.group(1)
                            # Normalize team names (CLI compatibility)
                            current_team = self._normalize_team_name(team_name)
                            current_team_ref = team_name

                            # Extract owners if specified in the comment
                            current_owners = self._extract_owners_from_line(line)
                        else:
                            # Try GitHub team pattern (@org/team)
                            github_match = GITHUB_TEAM_PATTERN.search(line)
                            if github_match:
                                team_name = github_match.group(1)
                                # Handle org/team format
                                if "/" in team_name:
                                    current_team = (
                                        team_name.split("/")[-1]
                                        .replace("-", " ")
                                        .title()
                                    )
                                    current_team_ref = team_name
                                else:
                                    current_team = team_name.replace("-", " ").title()
                                    current_team_ref = team_name
                        continue

                    # Parse directory mapping
                    parts = line.split()

                    if not parts:
                        continue

                    path_pattern = parts[0]

                    # Skip regex patterns (lines starting with ^)
                    if path_pattern.startswith("^"):
                        continue

                    # Extract owners from this line
                    line_owners = self._extract_owners_from_line(" ".join(parts[1:]))

                    # If no team context from comment, try to extract from owners
                    if current_team == "Unknown" and line_owners:
                        current_team = self._extract_team_from_owner(line_owners[0])

                    # Normalize path pattern
                    normalized_pattern = path_pattern.lstrip("/")

                    # Handle glob patterns like **/charts/
                    if "**" in normalized_pattern:
                        normalized_pattern = normalized_pattern.split("**/")[-1]

                    # Store team info
                    team_info = TeamInfo(
                        name=current_team,
                        pattern=normalized_pattern,
                        owners=line_owners or current_owners,
                        team_ref=current_team_ref,
                    )
                    self.teams.append(team_info)

                    # Build path -> team mapping
                    if normalized_pattern.endswith("/"):
                        dir_name = normalized_pattern.rstrip("/")
                        self.team_mapping[dir_name] = current_team
                    elif "*" in normalized_pattern:
                        prefix = normalized_pattern.rstrip("*")
                        if prefix:
                            self.team_mapping[prefix] = current_team
                    else:
                        self.team_mapping[normalized_pattern] = current_team

        except OSError:
            return

    def _extract_owners_from_line(self, line: str) -> list[str]:
        """Extract owner references from a line."""
        owners: list[str] = []

        # Extract GitHub team mentions
        for match in GITHUB_TEAM_PATTERN.finditer(line):
            owner = match.group(0)
            if owner not in owners:
                owners.append(owner)

        # Extract email patterns
        for match in EMAIL_TEAM_PATTERN.finditer(line):
            owner = match.group(1)
            if owner not in owners:
                owners.append(owner)

        return owners

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for consistent display."""
        name = name.lstrip("@")
        return name.replace("_", "-").title()

    def _normalize_team_name(self, name: str) -> str:
        """Normalize a team name for consistent display."""
        return self._normalize_name(name)

    def _extract_team_from_owner(self, owner: str) -> str:
        """Extract a team name from an owner reference."""
        owner = owner.strip()

        # Handle GitHub team mentions
        if owner.startswith("@"):
            team = owner.lstrip("@")
            if "/" in team:
                team = team.split("/")[-1]
            return self._normalize_name(team)

        # Handle email pattern
        if "@" in owner:
            team = owner.split("@")[0]
            return self._normalize_name(team)

        return self._normalize_name(owner)

    def get_team_for_path(self, chart_path: Path) -> str | None:
        """Get team name for a chart path."""
        chart_name = chart_path.name

        # Direct match first
        if chart_name in self.team_mapping:
            return self.team_mapping[chart_name]

        # Try longest prefix match for nested directories
        best_match: str | None = None
        best_match_length = 0

        for pattern, team in self.team_mapping.items():
            if chart_name.startswith(pattern):
                match_length = len(pattern)
                if match_length > best_match_length:
                    best_match = team
                    best_match_length = match_length

        return best_match

    def get_all_teams(self) -> list[str]:
        """Get list of all unique team names."""
        unique_teams = {team.name for team in self.teams}
        unique_teams.update(self.team_mapping.values())
        return sorted(unique_teams)
