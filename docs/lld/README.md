# Helix — low-level design

This LLD refines the [high-level design](https://claude.ai/code/artifact/079f03ac-c7a6-4776-989d-83eb47cf297b) (exported in this repository as [`ai-builder-hld.md`](../../ai-builder-hld.md)) of Helix. Helix takes a Jira Cloud ticket and turns it into a reviewed GitHub pull request for a Mule 4.9 application. It runs beside Meridian 1.8.1 and imports it. The plan, [`ai-builder-plan.md`](../../ai-builder-plan.md), is the source of truth; the plan and the HLD call the product *the builder*, its name until decision 9 named it Helix.

Every design decision carries a status tag (`00-conventions.md` §1). Items tagged `[HLD-P#n]` resolve a design gap the HLD found. They are proposals that wait on the owner's approval, and `[VERIFY]` marks an external product fact to confirm before it is relied on. Nothing is built yet.

## Reading order

| File | Sub-phase | What it covers |
| --- | --- | --- |
| [00 — Conventions](00-conventions.md) | all | Binding names, status tags, CLI surface, `PhaseOutcome`, storage paths, schema owners, process classes, credential model, sandbox environment allowlist |
| [01 — Repository and runtime](01-repository-and-runtime.md) | B1, all | Repository layout, packaging, container images, the B2 pilot workflow, `helix run`, the Meridian bridge and its contract tests, CI policy |
| [02 — Client profile and doctor](02-client-profile-and-doctor.md) | B1 | `helix.yaml` schema with an annotated fixture, loader rules, the doctor's ONB-01 to ONB-38 checks, ONBOARDING.md |
| [03 — Control plane](03-control-plane.md) | B2–B5 | Webhook receiver, Jira client, credential broker, model gateway, Maven proxy, git writer, vault, egress guard and `egress_policy.v1` |
| [04 — Agent runtime](04-agent-runtime.md) | B2–B5 | Agent SDK session runner, `phase_brief.v1` and `phase_result.v1`, tool and hook policy, skills, sandbox container, injection hook points |
| [05 — B3: Discover, intake and clarification](05-b3-intake-discover.md) | B3 | Discover, `fact_sheet.v1`, the answer ledger, question sets, the threshold, Draft, gate 1 |
| [06 — B4: Design](06-b4-design.md) | B4 | Decision table, contract and ruleset check, the integration HLD and LLD, naming, key list, `design_bundle.v1`, the draft PR for gate 2 |
| [07 — B2: Build, test and pull request](07-b2-build-test-pr.md) | B2 | Scaffold, golden parent pom, property layout, Maven, `meridian report`, MUnit, mutation check, PR flow, re-verification |
| [08 — B5: Durable orchestration](08-b5-orchestration.md) | B5 | Temporal topology, `TicketWorkflow` state machine, signals, `gate_approval`, off-path transitions, caps, operations |
| [09 — Audit, metering and measurement](09-audit-metering-measurement.md) | B2–B5 | `audit_event.v1` through Meridian's `RunLog`, chain anchoring, `meter_event.v1`, cap arithmetic, *accepted* and reviewer minutes |
| [10 — Security and test plan](10-security-and-test-plan.md) | all | Threat model, per-hop residency, egress requirements, injection corpus, the full guard catalogue, fixtures, CI, Definition-of-Done traceability |
| [11 — B6: Deploy interface (sketch)](11-b6-deploy-interface.md) | B6, not built | What B1–B5 reserve so deploy stays open; the two open B6 questions |

## Findings from the Meridian source that change the plan

- **`MERIDIAN_HOME`, not `MERIDIAN_STATE_DIR`.** Meridian 1.8.1 reads only `MERIDIAN_HOME` (`meridian/settings.py:74`). Helix exports that variable and never sets the plan's name (00 §7, §9).
- **A chain file cannot be resumed.** `RunLog` always starts a file at an all-zero previous hash (`runlog.py:97`). So the chain is one segment per phase attempt, linked as 09 describes (01 §3.5, 09 §3.3).
- **`settings.reload()` does not rebind everything.** The state directory, run-log directory, credential cache directory and `.env` snapshot stay as first imported. A profile is bound once per fresh process (01).
- **Meridian has a fourth exit code.** `EXIT_PREFLIGHT = 3` exists in `cli.py`. The bridge treats any code other than 0–2 as `FAILED` (01 §3.5.3, 10 §6).
- **Fixture prefixes.** Meridian's default prefix is `acme`, so the two fixture clients are `acme-a` and `acme-b`, with grammar prefixes `acmea` and `acmeb` (10 §3.11).

## Owner decisions this LLD raises

These are on top of plan decisions 5–12 and the HLD gaps. The first two change something the plan states.

| Decision | Default in this LLD | Where |
| --- | --- | --- |
| Run the pilot with plain workflow steps calling `helix run` instead of `claude-code-action` | Plain steps, so the sandbox environment stays exhaustive (HLD-P#1, #4) | 01 §3.8 |
| Write `deployment_properties` at gate 3 rather than at build | Gate 3 | 02 §3.10, 06, 07 |
| Pilot repository and runners | Client's organisation, owner-run self-hosted runners in the client's region | 01 §3.8 |
| Pilot dispatch credential | The GitHub App's narrowed token | 01 §3.8, 02, 03 §3.2 |
| Temporal: self-hosted or managed; namespace or task queue per client | See 08's recommendation | 08 §6 item 8 |
| Long-lived per-client pollers or a worker pair per workflow | Pollers with a fresh unit per activity | 08 §6 item 13 |
| Meridian contract surface wider than the plan's three imported names | Widened, held by contract tests | 01, 03, 07, 11 |
| Render higher-environment property files from the key list instead of `prepare --write` | `prepare --write` (plan) | 07 §6 |
| Decision 12's "reviewer minutes under 90" | Gate 3 active minutes | 09 §6 O7 |
| Tools' own outbound calls (CLI telemetry, Maven, Mule runtime) | Each switched off or quietly refused, case by case | 10 §3.5 rule 6 |
| A draft reviewer's release counts as "a human sending it" (decision 10) | Yes | 03 §6 item 10 |
| Vendor the Meridian wheel; move the plan into `docs/PLAN.md` | Yes | 01 §6 |

## Traceability

**Plan sub-phases → files**

| Sub-phase | Primary | Also |
| --- | --- | --- |
| B1 profile, prerequisites, spike | 02 | 01 (images, bridge, spike), 10 |
| B2 build, test, PR as a GitHub Action | 07 | 01 (pilot workflow), 03, 04, 09 |
| B3 intake, Discover, clarification | 05 | 03 (receiver, Jira, Draft), 04, 08 |
| B4 design | 06 | 04, 07 (draft PR), 08 |
| B5 orchestration, audit, metering | 08 | 09, 03, 10 |
| B6 deploy (sketch) | 11 | 02 (no deploy credential), 08 (reserved queue) |

**Plan §7 Definition of done → tests.** 10 §5.10 maps each item to guard ids. In summary:

| Item | Guards (10 §5) |
| --- | --- |
| 1 Profile, doctor, two clients | G-B1-01 to G-B1-11, G-B5-17, G-P13-10, G-P13-11, G-L-04 |
| 2 Fact sheet to PR, measured | G-B2-01 to G-B2-20, G-P04, G-P05, G-P08, G-P09, G-P17-b, G-P18 |
| 3 One question set, never asked twice | G-B3-01 to G-B3-11, G-L-03, G-R06 |
| 4 Contract and key list | G-B4-01 to G-B4-07, G-P10-a |
| 5 Restart, chain, cap, corpus, no deploy | G-B5-01 to G-B5-19, G-P13, G-P15, G-P16-a, G-L-01, G-B1-09 |
| 6 Every guard both ways | G-X-01 to G-X-07, G-R11-a |
| 7 A newcomer reaches a merged PR | Evidence in a done note; no automated test |

**HLD gaps → files**

| Gap | Implemented in |
| --- | --- |
| HLD-P#1 Credentials split from agents | 00 §9, 03 §3.6 (broker), 04 (sandbox environment), 01 §3.5 (bridge environment) |
| HLD-P#2 Model gateway | 03 §3.7, 04, 09 (meter) |
| HLD-P#3 Untrusted text | 04, 05 (`fact_sheet.v1`) |
| HLD-P#4 Pilot exposure | 01 §3.8, 03 §3.2 |
| HLD-P#5 Maven proxy and pom guard | 03 §3.8, 07 (PG1–PG8) |
| HLD-P#6 Control plane and vault | 03 |
| HLD-P#7 Gate integrity | 08 §3.9 (`gate_approval`), 05 (gate 1), 06 (draft PR), 07 §3.11.1 |
| HLD-P#8 Re-verification | 07 §3.8.7, 03 §3.9 |
| HLD-P#9 Placeholders and property layout | 07, 11 (key-holder step) |
| HLD-P#10 Exchange and connected apps | 02, 03, 06 |
| HLD-P#11 Repositories | 00 §3, 01, 02 |
| HLD-P#12 Runtime before B5 | 08, 05 |
| HLD-P#13 Tenancy | 08, 03, 01 |
| HLD-P#14 Residency | 10 §3.4–§3.5, 02, 03 §3.10 |
| HLD-P#15 Cost | 03 §3.7, 09, 08 |
| HLD-P#16 No mid-phase approvals | 04 (hooks), 07 §3.11.1 |
| HLD-P#17 Phase outcomes | 00 §5, 07, 08 |
| HLD-P#18 Measurement | 09, 07 |
| HLD-P#19 Operations | 08 |
| Lower items | Chain anchoring 09; GitHub settings 02, 03 §3.9; webhook hardening 03 §3.4; Jira onboarding 02; mutation choice 07; Meridian surface 01; hosted-agent revisit 01 |
| Review items 6 and 11 | Question-set leakage: 03 §3.5.5, 05; DX MCP spike criteria: 01, 10 |

**Open plan decisions → files**

| Decision | Affects |
| --- | --- |
| 5 Repository shape | 01 (and the contract widening in 03, 07, 11) |
| 6 Gate signers and turnaround | 02, 08, 09 |
| 7 Mandatory design artefacts (blocks B4) | 02, 06 |
| 8 Deploy route | 11 |
| 9 Name: answered, Helix | 00, 01 |
| 10 Outbound messages | 02, 03, 05, 08 |
| 11 Dollar cap | 02, 03, 08, 09 |
| 12 Pilot acceptance target | 09, 07 |

## `[VERIFY]` items and open items

Each file lists its own in its last section. Counts of `[VERIFY]` marks: 00: 7 · 01: 36 · 02: 42 · 03: 63 · 04: 48 · 05: 18 · 06: 26 · 07: 46 · 08: 36 · 09: 25 · 10: 27 · 11: 32. Most concern GitHub, Jira, Anypoint CLI and DX MCP Server behaviour, Temporal details and Agent SDK specifics. Settle them before the code that depends on them is written.

## How this LLD was produced

Each section was written against the plan, the HLD and the Meridian source. An independent reviewer then checked it adversarially, and a fixer applied the findings it confirmed. A cross-file critic then compared every file against the others and 00. Its findings were fixed per file, and a final pass reconciled the rest by hand: git-writer function names, the `egress_policy.v1` owner, the pilot gate record, draft-hold states, the cap error prefix and fixture names.
