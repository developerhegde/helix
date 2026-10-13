# Architecture decision — profile schema reconciliation

**Date:** 2026-10-12. **Status:** decided on the recommendation the owner asked for; any row can be reopened.

## Problem

Two documents describe `helix.yaml`. The B1 contract (`b1-client-profile-and-doctor.md`) defines version 1, which is built and tested. LLD `02-client-profile-and-doctor.md` describes a fuller profile with different names for the same things, and stricter or looser rules in places. LLD 02 §6 lists thirteen differences.

## Principle

1. **Version 1 as built is the base.** Its field names stay. The B1 contract already allows only additive change until a migration command exists.
2. **LLD 02's extra content arrives as additions**, each in the sub-phase that first needs it, under the B1 contract's names.
3. **One source per fact.** Where the same fact is stated in two places, one is named the source and the other must agree or is dropped.
4. **Helix never writes to a profile.** Anything Helix records goes to the Helix store.

## Decisions

| # | Difference | Decision |
| --- | --- | --- |
| 1 | Schema marker, identity, unknown keys | `schema_version: 1` stays. `client_id` keeps the B1 pattern and now must equal the profile directory's name (**B1-017**, built). An unknown top-level key is a warning (**B1-018**, built): a normal run reports it, `--strict` refuses it, and the schema can still grow by addition. |
| 2 | Model route and caps | The B1 names stay: `model_route.phases.*`, `run_cap_usd`, `phase_cap_usd`. LLD 02's other limits (monthly and daily ceilings, turns, retry cap, rate limit, kill switch) enter as an additive `caps` block in B2. |
| 3 | Data handling | The profile states the client's requirements (`permitted_regions`, `zero_data_retention_required`, `allowed_hosts`). The policy table states the facts about providers and models. LLD 02's `forbidden_models`, `redact_before_model`, `hops[]` and `client_statement` are additions for B2 and B3. |
| 4 | Secret references | The `vault` block and `vault://` references stay. LLD 02's rule refusing them is withdrawn. A reference must sit under `vault.scope` (to build; the `acme-a` fixture's references do not, and are corrected with it). LLD 03's catalogue names the secrets inside that scope. |
| 5 | Jira | The B1 names stay (`cloud_id`, `bot_account_id`, `statuses.*`). Transition ids, issue types, fields, the webhook and the requester policy enter as an additive `jira.workflow` block in B2 and B3. |
| 6 | GitHub | The B1 names stay (`organisation`, `bot_account`, `repositories`, `allowed_bots`). App details and per-repository settings enter as additions in B2. The bot-approval proof is **not** written into the profile: it is a row in the Helix store's `onboarding_evidence` table. |
| 7 | Anypoint | One business group, one connected-app reference and one expiry stay for B1 and the B2 pilot. More than one connected app enters as an additive `anypoint.connected_apps` map when an activity needs its own. The warning horizon stays in the policy table. |
| 8 | Environments stated twice | `naming.environments` is the one list of environments. Each entry gains an optional `platform_name`. `anypoint.environments` stays as the allow-list of platform names: every non-production naming environment's `platform_name` must be in it, and no production one may be (to build). |
| 9 | Design standards stated three times | The client standards bundle is the source. The profile's `design` block is deprecated: it stays readable in version 1 and the migration removes it. LLD 02's `design_standards` block is withdrawn. Until the migration, the doctor should refuse a `design` block that disagrees with the bundle (to build; the two spell some values differently, for example `oas3` and `oas30`, so the check needs a value map). |
| 10 | Gates | The B1 names stay: `gates.{requirement, design, merge, deploy}` as lists of people. `gates.deploy` stays required: it names who will own gate four and grants nothing in B1–B5. LLD 02's rule that it be absent is withdrawn. |
| 11 | Files read from the profile directory | Helix reads `helix.yaml` and the standards bundle's material. Everything else the client supplies lives under `standards/` and is listed in the bundle by path and digest: the deny-list, the skills text and the decision table (bundle `files[]`, to build). Evidence files are not profile content: they are passed to the readiness doctor explicitly and recorded in `onboarding_evidence`. No command searches for a profile; `$HELIX_PROFILES_ROOT/{client_id}/` is only how the control plane forms the explicit path it passes. |
| 12 | Doctor and loader interface | The built interface stays: `helix doctor --profile <path> [--format text\|json] [--strict]`, B1 rule ids, the JSON result, `load_profile(profile_dir, *, now, policy)`. The connected checks of B2 arrive as an added `--scope` on the same command, reporting ONB items beside the B1 rules. A required check that could not run exits 1, as conventions §5 says; exit 2 is only an operational failure. `helix profile validate` is withdrawn: the offline `helix doctor` is that check. |
| 13 | Blocks only LLD 02 has | Each enters as an addition in the sub-phase that needs it: `caps` and `maven` in B2, `intake` and `discover` in B3, `orchestration` in B5, and so on. None is required by the B1 doctor. |

## Built with this decision

- **B1-017**: `client_id` equals the profile directory's name. Error.
- **B1-018**: an unknown top-level key. Warning.
- **B1-009, extended** (decision 4): every `vault://` reference sits inside `vault.scope`; the `acme-a` fixture is corrected.
- **B1-019** (decision 9): the `design` block and the naming layout agree with the standards bundle, with the short spellings (`oas3`, `json-logger-module`) accepted as equal.
- **B1-020** (decision 8): a naming environment's `platform_name` is in `anypoint.environments` exactly when the environment is non-production.
- **B1-016, extended** (decision 11): the bundle's `files[]` (purposes `denylist`, `skills`, `decision_table`), each beside the bundle with a matching digest.
- Doctor findings are sorted by rule id, so the order is stable whatever order the checks run in.

## To build

| Item | From decision |
| --- | --- |
| `onboarding_evidence` rows for the bot-approval proof and for evidence files (needs the Helix store, B2) | 6, 11 |
| `--scope` and the ONB items on `helix doctor` (B2 readiness) | 12 |
| A profile migration command, before any rename or removal | 9, principle 1 |
| Consumers of the bundle-listed files: the deny-list scanner (`helix.clientdata`), the skills text and the decision table | 11 |

## Effect on other documents

- **B1 contract**: gains B1-017 to B1-020 and the extensions to B1-009 and B1-016.
- **LLD 02**: its §6 rows are closed against this document. Its field reference (§3.4) and example (§3.5) still use the earlier names and are to be re-expressed in the B1 names; until then this document governs.
- **LLD 00**: `helix profile validate` is withdrawn from the command table.
- **LLD 07**: the bot-approval proof is recorded in `onboarding_evidence`.
