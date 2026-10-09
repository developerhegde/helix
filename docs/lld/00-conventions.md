# 00 — Conventions and shared contracts

Every other file in `lld/` uses the names, enums, schemas and credential model defined here. If a section file needs a new shared identifier, it is added here first.

Sources: [`ai-builder-plan.md`](../../ai-builder-plan.md) (the plan) and [`ai-builder-hld.md`](../../ai-builder-hld.md) (the HLD, including its *Design gaps and proposed resolutions* table) at this repository's root; and, outside this repository, the Meridian source tree (`meridian/`, the `meridian` package) for every interface Helix imports or runs.

## 1. Status tags

Every design decision in the LLD carries one tag, so a reader can tell what is settled.

| Tag | Meaning |
| --- | --- |
| `[PLAN]` | Stated in the plan; not open to change in the LLD |
| `[PLAN-DEFAULT n]` | The default of open decision *n* in the plan §4; changes if the owner decides otherwise |
| `[HLD-P#n]` | Resolves HLD design gap *n*; a proposal pending the owner's approval. Removing it must not break the rest of the design without that file saying how |
| `[LLD]` | This LLD's own choice where the plan and HLD are silent; reversible |
| `[VERIFY]` | An external product fact (Jira, GitHub, Anypoint, Agent SDK) not proven in the plan; confirm at implementation, before relying on it |

## 2. Technology baseline

| Item | Choice | Tag |
| --- | --- | --- |
| Helix language | Python 3.14 (Meridian is Python; imported as a wheel) | `[LLD]` |
| Meridian | Version-pinned wheel; only `meridian_bridge` imports it | `[PLAN-DEFAULT 5]` |
| Orchestration | Temporal (MIT), Python SDK | `[PLAN]` |
| Agent runtime | Claude Agent SDK for Python (`claude-agent-sdk`) | `[PLAN]` |
| Model gateway | Anthropic Python SDK (`anthropic`): `Anthropic`, `AnthropicBedrockMantle`, `AnthropicVertex` clients | `[HLD-P#2]` |
| Helix store | PostgreSQL 16 (ledger, deliveries, runs, gates, meter); also Temporal's persistence | `[LLD]` |
| Mule toolchain on workers | JDK 17, Maven 3.9.x, Node 20 LTS, Anypoint CLI v4 with the DX plugin, DX MCP Server only if the spike passes | `[PLAN]` |
| Generated apps | Mule 4.9.x LTS current patch, MUnit 3.7.4, OAS 3.0 default | `[PLAN]` |
| Diagrams in LLD files | Mermaid code blocks | `[LLD]` |

Default model for every phase is `claude-opus-5-5`; the profile may set a different model per phase, subject to the client's data rules (decision 1). `claude-fable-5-1` requires 30-day retention and is refused by the doctor under a zero-data-retention profile. On Bedrock, model IDs take the `anthropic.` prefix; on Vertex they are the bare IDs. `[PLAN]` for routing, `[LLD]` for the default.

## 3. Repository layout `[PLAN-DEFAULT 5]` `[LLD]`

The product display name is **Helix** and its canonical technical identifier is `helix`. Product-facing prose uses `Helix`; packages, console commands, environment-variable prefixes, container paths, image names, branch prefixes, and generated operational identifiers use the canonical identifier. A future rename changes the product-identity manifest and its generated consumers, rather than scattering literal names through the implementation.

**Product identity manifest** `[LLD]`. `src/helix/product_identity.py` is the sole source of truth for the display name, canonical identifier, environment-variable prefix, container-path segment, branch prefix, and default image-name prefix. Code, template rendering, CLI banners, generated Jira text, and image metadata import or render from it. A guard rejects a product-name literal outside this module, packaging metadata, immutable documentation/history, and fixture assertions. Renaming is a deliberate migration: update the manifest, package metadata, and generated templates; regenerate checked templates; migrate external identifiers only when each client is re-onboarded; retain the previous identifier as an accepted read-only alias only when an explicit migration requires it.

```
helix/                          repository root (new repository)
  pyproject.toml                  pins meridian==<version>, anthropic, claude-agent-sdk, temporalio
  src/helix/
    cli/                          `helix` entry point and sub-commands (section 4)
    profile/                      schema, loader, doctor
    controlplane/
      webhook/                    receiver, HMAC, dedup, routing
      jira/                       REST client, status mapping, comment templates
      gitwriter/                  GitHub App client, PR assembly
      broker/                     credential broker (connected-app exchange)
      gateway/                    model gateway
      mavenproxy/                 Nexus-authenticating repository proxy
      vault/                      vault adapter
    agents/
      runner.py                   Agent SDK session runner
      hooks.py                    PreToolUse policy
      definitions/{intake,design,build,test}/   system prompt, tool policy, skills list
    phases/                       discover, intake, design, build, test, pr: one module per CLI
    orchestration/                Temporal workflow, activities, worker bootstrap
    audit/                        runlog wrapper, chain anchoring
    metering/                     meter events, pricing, caps
    meridian_bridge/              the only package that imports meridian
    schemas/                      JSON Schemas listed in section 8
  skills/                         skills files mounted read-only into agent sandboxes
  templates/                      golden parent pom, property files, PR body, integration HLD/LLD templates
  tests/{unit,contract,guards,integration}/  and tests/fixtures/acme-*/
  docs/                           QUICKSTART.md, ONBOARDING.md, RUNBOOK.md
  containers/                     controlplane.Dockerfile, worker-build.Dockerfile, worker-agent.Dockerfile
```

Generated Mule applications never live here: they live in the client's GitHub organisation, one repository per integration unless the client's convention says otherwise `[HLD-P#11]`. This repository holds only `acme-*` fixtures `[PLAN]`.

## 4. CLI surface — parity `[PLAN]`

Every phase is a CLI; the GitHub Action, the Temporal activity and a terminal run the same command. Common flags on phase commands:

| Flag | Meaning |
| --- | --- |
| `--profile DIR` | The client's profile directory |
| `--ticket KEY` | Jira issue key, for example `ACME-123` |
| `--run-dir DIR` | The run's artefact directory (section 7) |
| `--brief FILE` | `phase_brief.v1` input |
| `--out FILE` | `phase_result.v1` output |

| Command | Runs in | Purpose | Owning file |
| --- | --- | --- | --- |
| `helix profile validate` | anywhere | Schema and completeness check of a profile | 02 |
| `helix doctor` | control plane | All onboarding checks, numbered | 02 |
| `helix discover` | control plane | Exchange, `describe-connector`, Meridian tenant reads | 05 |
| `helix intake-prepare` | control plane | Classifies the wake and writes intake's inputs from the receiver's snapshot; no Jira call | 05 |
| `helix intake` | agent worker | Intake agent session | 05 |
| `helix intake-apply` | control plane | Admits answers, merges the ledger, then posts and transitions through file 03's Jira client | 05 |
| `helix design` | agent worker | Design agent session, then ruleset check | 06 |
| `helix build` | agent worker | Build agent session, then `mvn clean package` and `report` | 07 |
| `helix test` | agent worker | Test agent session, coverage, mutation check | 07 |
| `helix verify --stage {build,test,head}` | agent worker, no agent session | Independent verification: Maven, `report`, key list, mutation, secret scan | 07 |
| `helix pr` | control plane | Git writer: branch, commit, pull request, ticket link | 07 |
| `helix run` | terminal or Action | Runs a ticket's phases in order without Temporal (B2 pilot, parity) | 01 |
| `helix webhook serve` | control plane | Webhook receiver | 03 |
| `helix gateway serve` | control plane | Model gateway | 03 |
| `helix broker serve` | control plane | Credential broker | 03 |
| `helix maven-proxy serve` | control plane | Maven repository proxy | 03 |
| `helix worker --class {control,agent}` | worker | Temporal worker for a task-queue class | 08 |
| `helix orchestration {step,cutover,cancel}` | control plane | One control step as a fresh subprocess; cutover of in-flight driver tickets; cancel of waiting runs under the kill switch | 08 |
| `helix audit verify --run RUN_ID` | anywhere | Wraps `meridian runs --verify` | 09 |
| `helix meter report` | anywhere | Spend and measurement per run, phase, client | 09 |
| `helix meter measure` | control plane | Measurement for one run, or the window sweep: accepted, change requests, hand rewrites, minutes | 09 |
| `helix deploy …` | reserved | Reserved for B6: every sub-command exits 2 in B1–B5 | 11 |

## 5. Exit codes and phase outcomes

Exit codes are Meridian's `[PLAN]`: **0** nothing owed, **1** findings, **2** error. Doing nothing is never 0; a check that could not run is reported INCOMPLETE.

The workflow does not branch on exit codes; each phase CLI also writes a `PhaseOutcome` into `phase_result.v1` `[HLD-P#17]`:

| PhaseOutcome | Meaning | Exit code | Workflow action |
| --- | --- | --- | --- |
| `DONE` | Phase complete, nothing owed | 0 | Next phase |
| `AWAITING_REQUESTER` | Question set posted, ticket in *Needs info* | 1 | Wait for requester-comment signal |
| `AWAITING_GATE` | Ticket moved to a review status | 1 | Wait for the gate signal |
| `AWAITING_REPOSITORY` | Design bundle complete; its repository is missing or not onboarded (file 06) `[LLD]` | 1 | Wait for `repository_ready`, then re-run `helix pr --stage design`; `INCOMPLETE` when the wait times out |
| `REJECTED_TO_DESIGN` | Gate 2 rejected; reason captured | 1 | Re-run intake (reason) then design |
| `DESIGN_REFUSED` | The ruleset or a design post-check refused the draft, findings named; a design attempt is left (`design_standards.max_attempts`, file 06) `[LLD]` | 1 | Re-run design with the findings; with no attempt left, design itself ends `INCOMPLETE` |
| `RETRY_BUILD` | Red build or suite, retry budget left | 1 | Re-run build |
| `READY_FOR_REVIEW` | Pull request open and review-ready | 1 | Wait for merge signal |
| `INCOMPLETE` | A required check could not run, or PR opened without an accepted suite (draft) | 1 | Stop; post reason; excluded from measurement |
| `CAPPED` | A dollar or retry cap was reached | 2 | Stop at once; post where and what was spent |
| `FAILED` | Error | 2 | Fail the workflow; no automatic retry of the phase |

## 6. Identifiers and enums

| Name | Format or values | Tag |
| --- | --- | --- |
| `client_id` | `^[a-z0-9-]{2,32}$`; equals the profile directory name | `[LLD]` |
| `ticket_key` | Jira key, `^[A-Z][A-Z0-9]+-[0-9]+$` | `[PLAN]` |
| `run_id` | `{client_id}.{ticket_key}`: one run per ticket lifetime | `[HLD-P#15]` |
| `phase_attempt_id` | `{run_id}.{phase}.{n}`, `n` from 1 | `[LLD]` |
| `verify_attempt_id` | `{run_id}.verify.{n}`, `n` from 1: a head verification by `helix verify` in its own container (files 07, 08) | `[LLD]` |
| Temporal workflow id | `ticket/{client_id}/{ticket_key}` | `[LLD]` |
| `phase` | `discover`, `intake`, `design`, `build`, `test`, `pr`; `deploy` reserved for B6 | `[LLD]` |
| `gate` | `gate1_requirement`, `gate2_design`, `gate3_merge`, `gate4_deploy` (B6) | `[PLAN]` names, `[LLD]` keys |
| Logical ticket state | `new`, `needs_info`, `requirement_review`, `design_review`, `building`, `in_review`, `done`, `cancelled`, optional `draft`; `keys_filled`, `deploy_review`, `deployed` reserved for B6 (file 11) | `needs_info`, `requirement_review`, `design_review`, `draft`: `[PLAN]`; others `[LLD]` |
| Branch | `helix/{ticket_key}` in the generated-app repository | `[LLD]` |
| Fact status | `known`, `assumed`, `missing`, `changed` | `[PLAN]` |
| Fact id | `source`, `target`, `trigger`, `volume`, `sla`, `error_handling`, `security`, `mapping`, `environments` (extensible per profile) | `[PLAN]` |

The profile maps each logical ticket state, except those reserved for B6, to the client's Jira status name and transition id (`jira.states` in `helix.yaml`, file 02).

## 7. Storage locations

| What | Where | Tag |
| --- | --- | --- |
| Client profile | `$HELIX_PROFILES_ROOT/{client_id}/` holding `tenant.yaml`, `environments.yaml`, `compare.yaml`, `.env`, `helix.yaml` and `standards/` (the client's design standards, files 02 and 06); gitignored | `[PLAN]`; `standards/` `[LLD]` |
| Meridian state | `$HELIX_STATE_ROOT/{client_id}/meridian/`, exported as `MERIDIAN_HOME`; durable storage. The plan names `MERIDIAN_STATE_DIR`, but Meridian 1.8.1 reads only `MERIDIAN_HOME` (`meridian/settings.py:74`); Helix never sets `MERIDIAN_STATE_DIR` | `[PLAN]` location, Meridian source for the name |
| Run artefacts | `$HELIX_STATE_ROOT/{client_id}/runs/{ticket_key}/`: `discover.json`, `fact-sheet.json`, briefs, results, tool logs, reports; durable | `[LLD]` |
| Helix store | PostgreSQL database `helix`; every table carries `client_id` with row-level security per client | `[LLD]` |
| Activity workdir | `/work/{phase_attempt_id}/`: ephemeral, destroyed after the activity | `[HLD-P#13]` |
| Attempt spool | `$HELIX_SPOOL_ROOT/{client_id}/{attempt_id}/` with `in/` and `out/`, `attempt_id` being the `phase_attempt_id` or `verify_attempt_id`: plain files moved between the run directory and the agent host; an export separate from `$HELIX_STATE_ROOT`, which the agent host never mounts; ephemeral per attempt (file 08) | `[LLD]` |
| Skills | `/opt/helix/skills/` read-only mount | `[LLD]` |

## 8. Schemas and their owning files

All JSON documents carry `"schema": "<name>"` and are validated on read and write. Owning files define fields; others reference by name.

| Schema | Owner | Purpose |
| --- | --- | --- |
| `helix_profile.v1` (`helix.yaml`) | 02 | Per-client Helix configuration |
| `phase_brief.v1`, `phase_result.v1` | 04 | Input and output envelope of every phase CLI |
| `discover_findings.v1` | 05 | Discover output |
| `fact_sheet.v1` | 05 | The confirmed or draft fact sheet |
| `question_set.v1` | 05 | One round of numbered questions |
| Ledger tables `ledger_fact`, `ledger_answer` | 05 | Answer ledger |
| `decision_table.v1` | 06 | Pattern decision table, as data |
| `design_bundle.v1` | 06 | Contract, integration HLD and LLD paths, key list, names |
| `build_report.v1`, `test_report.v1` | 07 | Build and test evidence |
| `pr_provenance.v1` | 07 | Provenance block in the PR body |
| `webhook_delivery` table, `ticket_event.v1` | 03 | Inbound events after verification |
| `audit_event.v1` | 09 | Record shape written through `runlog.RunLog` |
| `meter_event.v1` | 09 | One record per model call |
| `gate_approval` table | 08 | Gate decisions with the digest of what was approved |
| `run_state.v1` | 01 | `helix run` progress record for the pilot and terminal parity |
| `doctor_report.v1`; table `onboarding_evidence` | 02 | Doctor results; verified onboarding-walk deliveries, written by file 03's receiver |
| `ticket_snapshot.v1`, `pr_snapshot.v1`; tables `ticket_cursor`, `outbound_hold`, `credential_lease`, `gateway_session`, `maven_access` | 03 | The receiver's copies of a ticket and a pull request; the mapped-event cursor, comments held for Draft, broker leases, gateway sessions, Maven access tokens |
| `egress_policy.v1` | 03 | Egress allowlist per container and per service; file 10 states the hosts each class may reach |
| `agent_submission.v1`, `agent_definition.v1`, `transcript.v1`, `tool_log.v1`, `env_snapshot.v1` | 04 | The agent's submitted result; the agent definition; session transcript, tool log and environment captured at agent start |
| `ticket_text.v1`, `intake_context.v1`, `ledger_snapshot.v1`, `rejection_context.v1`; table `intake_round` | 05 | Intake inputs and the ledger handed to design; a gate-2 rejection's reason; one row per intake comment |
| `design_resolutions.v1`, `estate_names.v1`, `standards_trace.v1` | 06 | Row choices from a gate-2 rejection; estate names for the collision check; each client standard traced to the rule, row or paragraph that applies it |
| `ticket_signal.v1`, `ticket_workflow_input.v1`, `ticket_workflow_state.v1`; tables `ticket_run`, `external_write`, `agent_job` | 08 | The one signal contract, filled by file 03; workflow input and state; run projection, external-write records, agent-job queue |
| `price_table.v1`, `audit_segment_header.v1`; tables `audit_segment`, `audit_event_key`, `meter_balance` | 09 | Model prices; first record of each audit segment; segments, event keys, cap balances |
| `injection_case.v1` | 10 | One case of the injection corpus |

Envelope fields common to `phase_brief.v1`: `schema`, `run_id`, `phase_attempt_id`, `client_id`, `ticket_key`, `phase`, `inputs` (map of artefact paths and their SHA-256), `caps` (`usd`, `max_turns`), `model`, `created_at`. Common to `phase_result.v1`: `schema`, `phase_attempt_id`, `outcome`, `exit_code`, `outputs` (paths and SHA-256), `findings[]`, `usage` (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `usd`), `started_at`, `ended_at`. File 04 owns the full definitions.

## 9. Process classes and credential model

Three process classes. Credentials never cross from the first into the second `[PLAN]` `[HLD-P#1]`.

| Class | Runs | Holds secrets? |
| --- | --- | --- |
| **Control plane** | webhook receiver, Jira client, git writer, credential broker, model gateway, Maven proxy, vault adapter, control-queue Temporal activities (`discover`, `pr`, posting, transitions) | Yes |
| **Agent sandbox** | `helix intake/design/build/test` with their Agent SDK session, on the agent task queue, one ephemeral container per activity | Only the tokens in the table below marked *reaches agent* |
| **Deploy worker** | Reserved for B6, per-client task queue; nothing in B1–B5 | — |

| Credential | Held by | Scope | Lifetime | Reaches agent? | Tag |
| --- | --- | --- | --- | --- | --- |
| Jira bot API token | Jira client | One bot account per client, Helix's project only | Vault rotation | Never | `[PLAN]` |
| GitHub App private key and installation token | Git writer | Write on the client's generated-app repositories; never admin, never a bypass actor | Installation token 1 hour `[VERIFY]` | Never | `[LLD]`, role `[HLD-P lower]` |
| Connected-app client id and secret | Credential broker | One app per client per Anypoint-using activity; non-production; expiry set | Secret expiry per doctor | Never | `[PLAN]` scope, `[HLD-P#10]` granularity |
| Anypoint bearer token | Broker issues to an activity | That connected app's grants; Exchange read only in B1–B5 | Platform-issued; never refreshed inside a sandbox | Build agent only, and only when the DX MCP route is used | `[HLD-P#1]` |
| Model-route credential (API key, AWS role, GCP service account) | Model gateway | Model invocation in the profile's region only | Vault rotation | Never | `[HLD-P#2]` |
| Gateway session token | Gateway issues per phase attempt | That attempt's models and dollar cap | Attempt duration, at most 6 hours | Yes, as `ANTHROPIC_AUTH_TOKEN` | `[HLD-P#2]` |
| EE Nexus credential | Maven proxy | Read-only | Vault rotation | Never | `[HLD-P#5]` |
| Maven proxy Exchange bearer | Maven proxy, from the broker (purpose `maven_exchange`) | The build app's Exchange read, for one client | Platform-issued; held in proxy memory | Never | `[LLD]` |
| Maven access token | Broker mints one per lease; the attempt's egress proxy holds it in memory | Reads under `/m2/{client_id}/` for one attempt | The lease's, at most 6 hours | Never: the launcher hands it to the egress proxy, not the sandbox | `[LLD]` |
| MUnit `license.lic` (vault `munit/license_lic`) | Vault, read by the control plane; mounted read-only, outside `/work`, only into `verify`-class containers | This client's MUnit runtime | The licence's | Never: `verify` containers run no agent session | `[PLAN]` question, `[LLD]` mechanism |
| Container registry pull credential | Each pilot runner host's Docker configuration; the owner's, not a client's | Read-only pulls of Helix's images from the owner's registry | Per the RUNBOOK | Never | `[LLD]` |
| Webhook HMAC secret | Webhook receiver, one per client | — | Vault rotation | Never | `[PLAN]` HMAC, `[HLD-P lower]` per client |
| Deploy-capable credential | Nothing in B1–B5; the doctor refuses one | — | — | Never | `[PLAN]` |

**Meridian's environment exports** `[PLAN]` exports, `[HLD-P#1]` placement. The plan's list is `MERIDIAN_TENANT_PROFILE`, `MERIDIAN_ENVIRONMENT_MAP`, `MERIDIAN_COMPARE_CONFIG`, `MERIDIAN_HOME` in place of the plan's `MERIDIAN_STATE_DIR`, `MERIDIAN_ENV_ALLOWLIST`, `MERIDIAN_AUTH_MODE=connected_app`, `ANYPOINT_CLIENT_ID` and `ANYPOINT_CLIENT_SECRET`. Helix adds `MERIDIAN_READ_ONLY=1`, `MERIDIAN_BROWSER_SSO=0`, `PYTHON_KEYRING_BACKEND` (the `keyring` null backend, `[VERIFY]` name) and, in control-class processes only, `MERIDIAN_ACTOR` (file 09's value) `[LLD]`. File 01 §3.5.2 owns the table per command: each Meridian subprocess gets an environment built from scratch, never inherited. The connected-app pair goes only into the environment of the one credentialed CLI, `tenant discover`, for that call, never into any process's `os.environ`. The other exports are set in control-plane processes; outside the control plane they reach only a subprocess's own `env`, never a process's `os.environ`. In the agent sandbox the only such subprocesses are the uncredentialed `report` and `prepare` that file 07 runs while no agent process exists; they receive the non-credential exports other than `MERIDIAN_ACTOR` `[HLD-P#1]` `[LLD]`, and the agent's allowlist below is unchanged.

**Agent sandbox environment — exhaustive allowlist** `[HLD-P#1]` `[HLD-P#2]`. The runner starts the Agent SDK with exactly these variables and nothing inherited:

| Variable | Value | Phases |
| --- | --- | --- |
| `ANTHROPIC_BASE_URL` | The model gateway's URL | all |
| `ANTHROPIC_AUTH_TOKEN` | Gateway session token | all |
| `CLAUDE_CODE_PROMPT_CACHE_TTL` | `1h` (the cold Maven run outlasts 5 minutes) | all |
| `HOME`, `PATH`, `LANG`, `TMPDIR` | Sandbox-local values | all |
| `HELIX_RUN_ID`, `HELIX_PHASE`, `HELIX_PHASE_ATTEMPT_ID` | Identifiers | all |
| `MAVEN_SETTINGS` path to a settings file naming only the proxy URL, no secret | | build, test |
| `ANYPOINT_BEARER` | Broker-issued bearer | build, only on the DX MCP route |

The intake agent's allowlist is the *all* rows only: it carries no Anypoint, Jira, GitHub or Nexus credential `[PLAN]`.

## 10. Verified Agent SDK facts (for files 04 and 08)

Checked against code.claude.com/docs/en/agent-sdk on 2026-10-08. Items marked `[VERIFY]` were not confirmed.

- Entry points: `query(prompt, options)` (one session) and `ClaudeSDKClient` (stateful). Helix uses `query()`: one session per phase attempt.
- `ClaudeAgentOptions` fields used: `allowed_tools`, `disallowed_tools`, `permission_mode` (Helix uses `"dontAsk"`, so anything not allowed is refused rather than asked `[VERIFY]` exact semantics), `system_prompt`, `cwd`, `add_dirs`, `env`, `mcp_servers` (stdio and in-process via `create_sdk_mcp_server` / `@tool`), `max_turns`, `max_budget_usd`, `model`, `setting_sources`, `hooks`, `can_use_tool`, `skills`.
- `setting_sources` defaults to user and project settings; Helix passes `[]` so no filesystem settings or `CLAUDE.md` load, and supplies skills explicitly `[VERIFY]` how skills load when `setting_sources` is empty.
- Hooks: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `UserPromptSubmit`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PermissionRequest`, `Notification`. `HookMatcher(matcher="Bash|Write|Edit", hooks=[cb], timeout=...)`; callback `async (input_data, tool_use_id, context) -> dict`. Deny: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}`.
- Gateway routing: `ANTHROPIC_BASE_URL` plus `ANTHROPIC_AUTH_TOKEN` (sent as a Bearer token); `ANTHROPIC_CUSTOM_HEADERS` available. With the gateway, no provider credential or `ANTHROPIC_API_KEY` is in the sandbox.
- Result: `ResultMessage` carries `session_id`, `total_cost_usd`, `subtype` (`success`, `error_max_turns`, `error_max_budget_usd`, ...) and `usage`. Per-call usage is metered at the gateway, not from the SDK `[HLD-P#15]`.
- Prompt caching is automatic; `CLAUDE_CODE_PROMPT_CACHE_TTL=1h` selects the one-hour window (Claude Code 2.1.242 or later). Changing tools, MCP servers or permission mode invalidates the cache, so each agent's tool set is fixed per definition.
- The SDK enforces no OS-level sandbox; network isolation is the container's job (egress allowlist, file 03 and 10).

## 11. Conventions for every LLD file

Each file follows this outline, dropping sections that do not apply:

1. **Purpose and scope** — one paragraph, with the sub-phase (B1–B6).
2. **Traceability** — plan sections, HLD sections and gap numbers it implements.
3. **Design** — modules and responsibilities, interfaces (CLI flags, HTTP endpoints, function signatures in prose), data (schemas with every field, types, constraints), sequences (Mermaid), configuration keys.
4. **Errors and exits** — every failure, its `PhaseOutcome`, exit code and what is posted on the ticket.
5. **Guards and tests** — each guard as a pair: the passing case and the failing case, with the fixture used.
6. **Open items** — anything `[VERIFY]` or awaiting an owner decision.

Write in plain English; numbers carry units or the word *estimate*; no client names other than `acme-*` fixtures.
