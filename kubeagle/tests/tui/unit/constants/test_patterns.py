"""Unit tests for regex patterns in constants/patterns.py.

Tests cover:
- All regex pattern constants
- Patterns compile successfully
- Pattern matching against expected inputs
"""

from __future__ import annotations

import re

from kubeagle.constants.patterns import (
    EMAIL_TEAM_PATTERN,
    GITHUB_TEAM_PATTERN,
    TEAM_PATTERN,
)

# =============================================================================
# TEAM_PATTERN
# =============================================================================


class TestTeamPattern:
    """Test TEAM_PATTERN regex."""

    def test_type(self) -> None:
        assert isinstance(TEAM_PATTERN, re.Pattern)

    def test_matches_team_prefix(self) -> None:
        match = TEAM_PATTERN.search("# TEAM: platform-team")
        assert match is not None
        assert match.group(1) == "platform-team"

    def test_matches_without_team_prefix(self) -> None:
        match = TEAM_PATTERN.search("# some-team-name")
        assert match is not None

    def test_matches_with_underscores(self) -> None:
        match = TEAM_PATTERN.search("# TEAM: my_team_name")
        assert match is not None
        assert match.group(1) == "my_team_name"

    def test_no_match_on_empty(self) -> None:
        match = TEAM_PATTERN.search("")
        assert match is None

    def test_case_insensitive(self) -> None:
        match = TEAM_PATTERN.search("# team: Alpha")
        assert match is not None


# =============================================================================
# GITHUB_TEAM_PATTERN
# =============================================================================


class TestGithubTeamPattern:
    """Test GITHUB_TEAM_PATTERN regex."""

    def test_type(self) -> None:
        assert isinstance(GITHUB_TEAM_PATTERN, re.Pattern)

    def test_matches_github_team(self) -> None:
        match = GITHUB_TEAM_PATTERN.search("@org/team-name")
        assert match is not None
        assert match.group(1) == "org/team-name"

    def test_matches_with_underscores(self) -> None:
        match = GITHUB_TEAM_PATTERN.search("@my_org/my_team")
        assert match is not None
        assert match.group(1) == "my_org/my_team"

    def test_no_match_without_at(self) -> None:
        match = GITHUB_TEAM_PATTERN.search("org/team-name")
        assert match is None

    def test_matches_without_slash(self) -> None:
        match = GITHUB_TEAM_PATTERN.search("@orgteam")
        assert match is not None
        assert match.group(1) == "orgteam"


# =============================================================================
# EMAIL_TEAM_PATTERN
# =============================================================================


class TestEmailTeamPattern:
    """Test EMAIL_TEAM_PATTERN regex."""

    def test_type(self) -> None:
        assert isinstance(EMAIL_TEAM_PATTERN, re.Pattern)

    def test_matches_email(self) -> None:
        match = EMAIL_TEAM_PATTERN.search("user@example.com")
        assert match is not None
        assert match.group(1) == "user@example.com"

    def test_matches_complex_email(self) -> None:
        match = EMAIL_TEAM_PATTERN.search("user.name+tag@sub.domain.org")
        assert match is not None

    def test_no_match_without_at(self) -> None:
        match = EMAIL_TEAM_PATTERN.search("not-an-email")
        assert match is None

    def test_no_match_without_domain(self) -> None:
        match = EMAIL_TEAM_PATTERN.search("user@")
        assert match is None


# =============================================================================
# __all__ exports
# =============================================================================


class TestPatternsExports:
    """Test that __all__ exports are correct."""

    def test_all_exports_importable(self) -> None:
        import kubeagle.constants.patterns as mod

        for name in mod.__all__:
            assert hasattr(mod, name), f"{name} listed in __all__ but not defined"
