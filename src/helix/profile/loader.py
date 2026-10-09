"""Profile loader: validates the profile before any phase starts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping, Optional

from .doctor import Report, evaluate
from .policy import DEFAULT_POLICY, Policy


class ProfileInvalid(Exception):
    """The profile has at least one error-severity finding."""

    def __init__(self, report: Report) -> None:
        super().__init__(f"profile has {report.errors} error(s)")
        self.report = report


@dataclass(frozen=True)
class Profile:
    root: str
    client_id: str
    data: Mapping[str, Any]
    report: Report


def load_profile(profile_dir: str, *, now: Optional[datetime] = None,
                 policy: Policy = DEFAULT_POLICY) -> Profile:
    report, doc = evaluate(profile_dir, now=now, policy=policy)
    if report.errors or doc is None or report.client_id is None:
        raise ProfileInvalid(report)
    return Profile(profile_dir, report.client_id, MappingProxyType(doc), report)
