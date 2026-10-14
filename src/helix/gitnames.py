"""Branch names and commit messages from the client standards bundle (STD-NAM-18, STD-NAM-19).

Pure functions: the git writer renders every branch and commit through them, and the
control plane maps a branch or pull request back to its ticket with ``ticket_from_branch``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Optional

DEFAULT_BRANCH_PATTERN = "feature/{ticket_key}-{slug}"
DEFAULT_COMMIT_PATTERN = "{ticket_key}: {summary}"
SUBJECT_LIMIT = 72  # the standard's maximum commit subject length
SLUG_LIMIT = 40
TICKET_KEY = re.compile(r"[A-Z][A-Z0-9]+-[0-9]+")  # conventions §6

_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_BAD_REF = re.compile(r"[\x00-\x20\x7f~^:?*\[\\]|\.\.|@\{|//|/\.|\.lock(?:/|$)")


class GitNameInvalid(ValueError):
    """A pattern, ticket key or rendered name breaks the naming rules."""


@dataclass(frozen=True)
class GitNaming:
    branch_pattern: str = DEFAULT_BRANCH_PATTERN
    commit_pattern: str = DEFAULT_COMMIT_PATTERN

    def __post_init__(self) -> None:
        _check_pattern(self.branch_pattern, {"ticket_key", "slug"}, "branch")
        _check_pattern(self.commit_pattern, {"ticket_key", "summary"}, "commit")
        if "{summary}" not in self.commit_pattern:
            raise GitNameInvalid("commit pattern must contain {summary}")

    def branch(self, ticket_key: str, title: str) -> str:
        """The branch for a ticket; the slug comes from the ticket's title."""
        name = self.branch_pattern.replace("{ticket_key}", _ticket(ticket_key)).replace("{slug}", slug(title))
        if not valid_ref(name):
            raise GitNameInvalid("rendered branch is not a valid git ref")
        return name

    def ticket_from_branch(self, branch: str) -> Optional[str]:
        """The ticket key a branch was rendered for, or None when the branch does not follow the pattern."""
        parts = re.split(r"(\{ticket_key\}|\{slug\})", self.branch_pattern)
        expression = "".join(
            f"(?P<ticket_key>{TICKET_KEY.pattern})" if part == "{ticket_key}"
            else _SLUG if part == "{slug}" else re.escape(part)
            for part in parts)
        match = re.fullmatch(expression, branch)
        return match.group("ticket_key") if match else None

    def commit_subject(self, ticket_key: str, summary: str) -> str:
        """One line of at most 72 characters; a long summary is cut at a word boundary."""
        line = " ".join(str(summary).split()).rstrip(".")
        if not line:
            raise GitNameInvalid("commit summary is empty")
        head = self.commit_pattern.replace("{ticket_key}", _ticket(ticket_key))
        room = SUBJECT_LIMIT - len(head.replace("{summary}", ""))
        if room < 10:
            raise GitNameInvalid("commit pattern leaves no room for a summary")
        if len(line) > room:
            cut = line[:room + 1].rsplit(" ", 1)[0] if " " in line[:room + 1] else line[:room]
            line = cut[:room].rstrip(" ,;:-")
        return head.replace("{summary}", line)


def from_standards(bundle: Mapping[str, Any]) -> GitNaming:
    review = bundle.get("review") if isinstance(bundle.get("review"), dict) else {}
    branch, commit = review.get("branch_pattern"), review.get("commit_pattern")
    return GitNaming(branch if isinstance(branch, str) and branch else DEFAULT_BRANCH_PATTERN,
                     commit if isinstance(commit, str) and commit else DEFAULT_COMMIT_PATTERN)


def slug(title: str) -> str:
    """Lowercase ASCII words of the title joined by hyphens, at most 40 characters, cut at a hyphen."""
    text = unicodedata.normalize("NFKD", str(title)).encode("ascii", "ignore").decode("ascii").lower()
    words = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(words) > SLUG_LIMIT:
        words = words[:SLUG_LIMIT + 1].rsplit("-", 1)[0] if "-" in words[:SLUG_LIMIT + 1] else words[:SLUG_LIMIT]
    return words.strip("-") or "change"


def valid_ref(name: str) -> bool:
    """The subset of `git check-ref-format` that a rendered branch can break."""
    return bool(name) and not (_BAD_REF.search(name) or name.startswith(("-", "/", "."))
                               or name.endswith(("/", ".")) or name == "@")


def _ticket(ticket_key: str) -> str:
    if not isinstance(ticket_key, str) or TICKET_KEY.fullmatch(ticket_key) is None:
        raise GitNameInvalid("ticket key is not a Jira key")
    return ticket_key


def _check_pattern(pattern: Any, allowed: set[str], kind: str) -> None:
    if not isinstance(pattern, str) or not pattern:
        raise GitNameInvalid(f"{kind} pattern is missing")
    names = _PLACEHOLDER.findall(pattern)
    if set(names) - allowed or names.count("ticket_key") != 1:
        raise GitNameInvalid(f"{kind} pattern must contain {{ticket_key}} once and only {sorted(allowed)}")
