# B1 implementation notes — client profile and doctor

Implements [`b1-client-profile-and-doctor.md`](b1-client-profile-and-doctor.md). This file records the choices the contract leaves to the implementation team, its resolved ambiguities, and the prerequisite register.

## Technology choices

| Item | Choice |
| --- | --- |
| Language | Python 3.14 (`pyproject.toml`), on the macOS and Windows dev machines |
| CLI framework | `argparse` (standard library), entry point `helix.cli.main:main` |
| Profile parsing | PyYAML `safe_load`, the only runtime dependency in B1 |
| Persistence | None: the doctor is read-only and stateless |
| Tests | Standard-library `unittest`, also collectable by pytest; run with `python -m unittest discover -s tests -t .` |

## Modules

| Path | Responsibility |
| --- | --- |
| `src/helix/product_identity.py` | Product identity manifest; profile file name and environment variable derive from it |
| `src/helix/profile/doctor.py` | Rules B1-001 to B1-014, `Finding`, `Report`, exit code |
| `src/helix/profile/loader.py` | `load_profile()`: refuses a profile with any error before a phase starts |
| `src/helix/profile/policy.py` | The local, versioned policy table |
| `src/helix/profile/secrets.py` | Secret tripwire: key name and value shape, paths only |
| `src/helix/profile/render.py` | Text and JSON output |
| `src/helix/cli/` | `helix doctor` |

## Decisions and resolved ambiguities

0. **Helix is standalone** (owner decision, 2026-10-09). It imports, reads, and validates nothing of Meridian's. The profile is `helix.yaml` only, B1-015 is withdrawn, and a guard test refuses any `meridian` reference in `src/` or `pyproject.toml`.
1. **Exit codes with warnings.** The contract's exit table lists "warnings only without `--strict`" under exit 1, but exit 0 and the `--strict` description say warnings fail only under `--strict`. Implemented: errors → 1; warnings only → 0, or 1 with `--strict`.
2. **Profile path.** `--profile` wins; `HELIX_CLIENT_PROFILE` is the only fallback. Both must be absolute. Nothing else is searched.
3. **Status values.** `healthy`, `warning`, `error`. JSON adds `deferred_checks` (additive), so automation can see that connected-system checks were not simulated.
4. **Dependent rules are skipped, independent ones all run.** A missing `helix.yaml` reports only B1-001 for it; an unsupported `schema_version` stops B1-003 to B1-013 but not the secret scan. A missing `data_handling` section reports B1-005 and skips B1-006.
5. **Allowed hosts (B1-006).** "Approved by the client's policy" is read as: every listed host must be in the policy table's hosts for the configured provider, with `{region}` filled from the model route. Entries may be a bare host or `https://host`; other schemes, ports and paths are refused.
6. **Production-like names (B1-011).** Case-insensitive match of the whole name or any alphanumeric token (`acme-PRD` is refused; `acme-product` is not) against `prod`, `production` and the table's aliases (`prd`, `live`).
7. **Findings never carry profile values.** Messages are fixed text; only the field path varies. YAML parser messages are dropped because they quote content. An internal error prints only the exception type.
8. **`client_id`** uses the contract's pattern. It is not compared with the directory name (LLD 00 §6 asks for that; the B1 contract does not).
9. **References.** `jira.webhook_secret_ref` and `anypoint.connected_app_ref` must be `vault://` references; a secret-named field holding anything other than a reference is a B1-014 finding.

## Deviations

| Item | Deviation | Reason | Closes in |
| --- | --- | --- | --- |
| Packaging | No `uv.lock`; only PyYAML is declared | B1 needs nothing else; `uv` is not installed on the dev machines | When B2 adds its dependencies |
| LLD | `docs/lld/` still describes Meridian integration (`meridian_bridge`, pinned wheel, Meridian CLIs and audit chain) | The standalone decision came after the LLD | LLD revision, before B2 design work |
| Test runtime | The suite ran on Python 3.14.8 on macOS only, in the project's `.venv` | The Windows dev machine has not run it yet | First run on Windows or in CI |

## Policy table

`policy.py`, version `1`, recorded in every doctor result. Provisional: it needs a named owner and release process before it decides production eligibility (contract challenge 3). Contents: per provider, zero-data-retention compatibility and approved hosts; models that require retention (`claude-fable-5-1`, from LLD 00 §2); production-like aliases; the 30-day expiry warning horizon. Any value change bumps the version.

## Schema evolution

`helix.yaml` is `schema_version: 1`; the doctor report is `schema_version: 1`. Only additive changes are allowed until a migration command and rollback policy exist (contract challenge 2). Unknown keys in `helix.yaml` are ignored.

## Prerequisite register

The doctor does not perform or simulate these. Each stays **pending** until its owner records evidence.

| Item | Owner | Status |
| --- | --- | --- |
| B1 spike (DX MCP Server and toolchain) | Helix owner | Pending |
| Vault: scope created, secrets stored, metadata readable | Client platform owner | Pending — B2 readiness check |
| Jira: bot account, project, three statuses, webhook | Client Jira admin | Pending — B2 readiness check |
| GitHub: organisation, bot, App installation, repositories onboarded | Client GitHub admin | Pending — B2 readiness check |
| Anypoint: non-production connected app, grants, secret expiry | Client Anypoint admin | Pending — B2 readiness check |
| Nexus: read-only credential behind the Maven proxy | Client platform owner | Pending — B2 readiness check |
| Model route: provider account, region, zero-data-retention terms | Client data owner | Pending — B2 readiness check |
| Policy table owner and release process | Helix owner | Pending |
