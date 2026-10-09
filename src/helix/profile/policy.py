"""Local, versioned policy table for the offline doctor (B1-005, B1-006, B1-011, B1-012).

Provisional: the table needs a named owner and release process before it can
decide production eligibility (B1 contract, challenge 3). Any change to a value
bumps ``version``, which the doctor records in its output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import FrozenSet, Mapping, Optional, Tuple


@dataclass(frozen=True)
class ProviderPolicy:
    zero_data_retention: bool
    hosts: Tuple[str, ...]  # "{region}" is replaced by the model route's region


@dataclass(frozen=True)
class Policy:
    version: str
    providers: Mapping[str, ProviderPolicy]
    retention_required_models: FrozenSet[str]
    production_aliases: FrozenSet[str]
    expiry_warning_days: int = 30
    bedrock_model_prefix: str = field(default="anthropic.")

    def approved_hosts(self, provider: str, region: str) -> Optional[FrozenSet[str]]:
        entry = self.providers.get(provider)
        if entry is None:
            return None
        return frozenset(h.replace("{region}", region) for h in entry.hosts)

    def requires_retention(self, model: str) -> bool:
        base = model[len(self.bedrock_model_prefix):] if model.startswith(self.bedrock_model_prefix) else model
        return base in self.retention_required_models

    def is_production_like(self, environment: str) -> bool:
        name = environment.strip().lower()
        tokens = [t for t in re.split(r"[^a-z0-9]+", name) if t]
        return name in self.production_aliases or any(t in self.production_aliases for t in tokens)


DEFAULT_POLICY = Policy(
    version="1",
    providers={
        "anthropic": ProviderPolicy(True, ("api.anthropic.com",)),
        "bedrock": ProviderPolicy(True, ("bedrock-runtime.{region}.amazonaws.com",)),
        "vertex": ProviderPolicy(True, ("{region}-aiplatform.googleapis.com",)),
    },
    # LLD 00 §2: this model requires 30-day retention, so a zero-data-retention profile refuses it.
    retention_required_models=frozenset({"claude-fable-5-1"}),
    production_aliases=frozenset({"prod", "production", "prd", "live"}),
)
