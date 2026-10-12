# Helix — low-level design

> Standalone revision, 2026-10-12: the overview, reading order and traceability now describe the standalone design and point to `docs/architecture/` for the decisions that replaced the Meridian integration.

This LLD refines the [high-level design](https://claude.ai/code/artifact/079f03ac-c7a6-4776-989d-83eb47cf297b) (exported in this repository as [`ai-builder-hld.md`](../../ai-builder-hld.md)) of Helix. Helix takes a Jira Cloud ticket and turns it into a reviewed GitHub pull request for a Mule 4.9 application. It is a standalone product: in B1–B5 it owns its naming, property files, validation, audit chain and profile, and needs no other tool's code, files, environment variables or state. A future Meridian integration may exist only behind an optional, version-pinned adapter that core Helix works without.

The plan, [`ai-builder-plan.md`](../../ai-builder-plan.md), and the HLD are historical input. The owner's standalone decision of 2026-10-09 and the decisions of 2026-10-12 are recorded in [`docs/architecture/`](../architecture/), and [`plan-amendments.md`](../architecture/plan-amendments.md) lists, statement by statement, what they replace in the plan and the HLD. Where the plan, the HLD or an LLD file differs from an architecture decision, the architecture decision governs.

Every design decision carries a status tag (`00-conventions.md` §1). Items tagged `[HLD-P#n]` resolve a design gap the HLD found. They are proposals that wait on the owner's approval, and `[VERIFY]` marks an external product fact to confirm before it is relied on. A decision that replaces a withdrawn mechanism is tagged *Standalone architecture decision*. B1 is built; B2 begins with the standalone naming contract, standards bundle, and local project validator.

## Architecture decisions to read first

| Document | What it decides |
| --- | --- |
| [B1 client profile and doctor](../architecture/b1-client-profile-and-doctor.md), [implementation notes](../architecture/b1-implementation-notes.md) | The profile is `helix.yaml` plus the client standards bundle it references, and nothing else; the offline `helix doctor` and rules B1-001 to B1-016; Python 3.14 |
| [B2 standalone Mule validation](../architecture/b2-standalone-mule-validation.md) | `helix validate` and `helix verify`, `validation_policy.v1`, `validation_report.v1`; what is deferred to an optional adapter |
| [B2 naming and environment contract](../architecture/b2-naming-and-environment-contract.md) | `helix.naming`, `naming_contract.v1`, environments, configuration paths, and the two layouts `environment_files` and `deployment_properties` |
| [B2 design bundle contract](../architecture/b2-design-bundle-contract.md) | The `design_bundle.v1` fields B2 reads; key classes; deployment property keys declared in the bundle only |
| [B2 Maven and MUnit execution contract](../architecture/b2-maven-munit-execution-contract.md) | The isolated Maven runner and the value-free evidence it produces |
| [Client standards bundle](../architecture/client-standards-bundle.md), [standards bundle mapping](../architecture/standards-bundle-mapping.md) | `client_standards_bundle.v1` as the source of client standards; the 94 rules of the reference standard and decisions D1 to D5, including the Mule file names and the branch pattern |
| [Plan amendments](../architecture/plan-amendments.md) | Where the standalone decisions amend the plan and the HLD |

## Reading order

A file revised to the standalone design carries a *Standalone revision* note under its title. A file without that note still describes the earlier design in places; the architecture decisions above govern until it is revised.

| File | Sub-phase | What it covers |
| --- | --- | --- |
| [00 — Conventions](00-conventions.md) | all | Binding names, status tags, CLI surface, `PhaseOutcome`, storage paths, schema owners, process classes, credential model, sandbox environment allowlist |
| [01 — Repository and runtime](01-repository-and-runtime.md) | B1, all | Repository layout, packaging on Python 3.14, container images, the B2 pilot workflow, `helix run`, CI policy |
| [02 — Client profile and doctor](02-client-profile-and-doctor.md) | B1 | `helix.yaml` schema with an annotated fixture, its `naming` block and standards bundle reference, loader rules, the doctor's ONB-01 to ONB-38 checks, ONBOARDING.md |
| [03 — Control plane](03-control-plane.md) | B2–B5 | Webhook receiver, Jira client, credential broker, model gateway, Maven proxy, git writer, vault, egress guard and `egress_policy.v1` |
| [04 — Agent runtime](04-agent-runtime.md) | B2–B5 | Agent SDK session runner, `phase_brief.v1` and `phase_result.v1`, tool and hook policy, skills, sandbox container, injection hook points |
| [05 — B3: Discover, intake and clarification](05-b3-intake-discover.md) | B3 | Discover, `fact_sheet.v1`, the answer ledger, question sets, the threshold, Draft, gate 1 |
| [06 — B4: Design](06-b4-design.md) | B4 | Decision table, contract and ruleset check, the integration HLD and LLD, names rendered by `helix.naming`, key list, `design_bundle.v1` with its standards and naming digests, the draft PR for gate 2 |
| [07 — B2: Build, test and pull request](07-b2-build-test-pr.md) | B2 | Scaffold, golden parent pom, property files rendered by Helix in either layout, Maven, `helix validate` and `helix verify`, MUnit, mutation check, PR flow, re-verification |
| [08 — B5: Durable orchestration](08-b5-orchestration.md) | B5 | Temporal topology, `TicketWorkflow` state machine, signals, `gate_approval`, off-path transitions, caps, operations |
| [09 — Audit, metering and measurement](09-audit-metering-measurement.md) | B2–B5 | `audit_event.v1` in the Helix-owned chain (`helix.audit.chain`), `helix audit verify`, chain anchoring, `meter_event.v1`, cap arithmetic, *accepted* and reviewer minutes |
| [10 — Security and test plan](10-security-and-test-plan.md) | all | Threat model, per-hop residency, egress requirements, injection corpus, the full guard catalogue, fixtures, CI, Definition-of-Done traceability |
| [11 — B6: Deploy interface (sketch)](11-b6-deploy-interface.md) | B6, not built | What B1–B5 reserve so deploy stays open; the hand-off contract with the client's deployment pipeline; what is withdrawn or left to an optional adapter |

## Findings from the Meridian source — withdrawn

Withdrawn (standalone decision): this section listed five findings from reading the Meridian source: its state-directory variable, its run-log files, its settings reload, its fourth exit code and its default fixture prefix. Helix no longer reads, imports or runs Meridian, so none of them shapes the design. One fact survives on its own: the two fixture clients are `acme-a` and `acme-b` (10 §3.11), and each takes its naming grammar from the `naming` block of its own fixture profile.

## Owner decisions this LLD raises

These are on top of plan decisions 5–12 and the HLD gaps. Rows marked *Withdrawn*, and the rows on property files, configuration layout and branch name, were settled by the decisions of 2026-10-09 and 2026-10-12; `docs/architecture/plan-amendments.md` has the detail.

| Decision | Default in this LLD | Where |
| --- | --- | --- |
| Run the pilot with plain workflow steps calling `helix run` instead of `claude-code-action` | **Decided:** plain steps, so the sandbox environment stays exhaustive (HLD-P#1, #4) | 01 §3.8 |
| Write `deployment_properties` at gate 3 rather than at build | **Withdrawn (standalone decision):** deployment property keys are declared in the design bundle only, and nothing is written to the profile at merge | 07 §3.4.4; B2 design bundle contract |
| Pilot repository and runners | Client's organisation, owner-run self-hosted runners in the client's region | 01 §3.8 |
| Pilot dispatch credential | The GitHub App's narrowed token | 01 §3.8, 02, 03 §3.2 |
| Temporal: self-hosted or managed; namespace or task queue per client | See 08's recommendation | 08 §6 item 8 |
| Long-lived per-client pollers or a worker pair per workflow | Pollers with a fresh unit per activity | 08 §6 item 13 |
| Meridian contract surface wider than the plan's three imported names | **Withdrawn (standalone decision):** nothing of Meridian's is imported or run, so there is no surface to hold | B2 validation decision |
| Render higher-environment property files from the key list instead of a `prepare` step | **Decided:** Helix renders every environment's files from the key list; there is no `prepare` step | 07 §3.4.4, §6 |
| Configuration layout: one file per environment, or one base and one secure file with the pipeline supplying the rest | **Decided:** both are supported; the profile's `naming.configuration.layout` chooses (mapping decision D1) | B2 naming contract; 07 §3.4.4 |
| Branch name | **Decided:** the standards bundle's `review.branch_pattern`, no longer a fixed name (mapping decision D4) | 00 §6; 07 §3.8.3 |
| Decision 12's "reviewer minutes under 90" | Gate 3 active minutes | 09 §6 O7 |
| Tools' own outbound calls (CLI telemetry, Maven, Mule runtime) | Each switched off or quietly refused, case by case | 10 §3.5 rule 6 |
| A draft reviewer's release counts as "a human sending it" (decision 10) | Yes | 03 §6 item 10 |
| Vendor the Meridian wheel | **Withdrawn (standalone decision):** no wheel is pinned or vendored | B1 implementation notes |
| Move the plan into `docs/PLAN.md` | Yes | 01 §6 |

## Traceability

**Plan sub-phases → files**

| Sub-phase | Primary | Also |
| --- | --- | --- |
| B1 profile, prerequisites, spike | 02 | 01 (images, spike), 10 |
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
| HLD-P#1 Credentials split from agents | 00 §9, 03 §3.6 (broker), 04 (sandbox environment) |
| HLD-P#2 Model gateway | 03 §3.7, 04, 09 (meter) |
| HLD-P#3 Untrusted text | 04, 05 (`fact_sheet.v1`) |
| HLD-P#4 Pilot exposure | 01 §3.8, 03 §3.2 |
| HLD-P#5 Maven proxy and pom guard | 03 §3.8, 07 (PG1–PG8) |
| HLD-P#6 Control plane and vault | 03 |
| HLD-P#7 Gate integrity | 08 §3.9 (`gate_approval`), 05 (gate 1), 06 (draft PR), 07 §3.11.1 |
| HLD-P#8 Re-verification | 07 §3.8.7, 03 §3.9 |
| HLD-P#9 Placeholders and property layout | 07 §3.4.4, 11 §3.10 (key-holder step) |
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
| Lower items | Chain anchoring 09; GitHub settings 02, 03 §3.9; webhook hardening 03 §3.4; Jira onboarding 02; mutation choice 07; hosted-agent revisit 01. Withdrawn (standalone decision): the item on Meridian's dependency surface, because there is no such dependency |
| Review items 6 and 11 | Question-set leakage: 03 §3.5.5, 05; DX MCP spike criteria: 01, 10 |

**Open plan decisions → files**

| Decision | Affects |
| --- | --- |
| 5 Repository shape | 01. Decided by the standalone decision: Helix's own repository, with no wheel pinned and no contract test against another tool (`docs/architecture/plan-amendments.md`) |
| 6 Gate signers and turnaround | 02, 08, 09 |
| 7 Mandatory design artefacts (blocks B4) | 02, 06; the client standards bundle is now their source (`docs/architecture/client-standards-bundle.md`) |
| 8 Deploy route | 11: the hand-off to the client's pipeline is the one core route |
| 9 Name: answered, Helix | 00, 01 |
| 10 Outbound messages | 02, 03, 05, 08 |
| 11 Dollar cap | 02, 03, 08, 09 |
| 12 Pilot acceptance target | 09, 07 |

## `[VERIFY]` items and open items

Each file lists its own in its last section. The per-file counts change as files are revised, so they are not repeated here; `grep -c '\[VERIFY' docs/lld/*.md` gives the current ones. Most concern GitHub, Jira, Anypoint CLI and DX MCP Server behaviour, Temporal details and Agent SDK specifics. Settle them before the code that depends on them is written. Anything a revised file marks *To design* is listed in that file's open items.

## How this LLD was produced

Each section was written against the plan and the HLD. An independent reviewer then checked it adversarially, and a fixer applied the findings it confirmed. A cross-file critic then compared every file against the others and 00. Its findings were fixed per file, and a final pass reconciled the rest by hand: git-writer function names, the `egress_policy.v1` owner, the pilot gate record, draft-hold states, the cap error prefix and fixture names.

Withdrawn (standalone decision): the first draft was also written against the Meridian source. The revision of 2026-10-12 removes that dependency file by file, following `docs/architecture/`. Where a replacement is designed, the file is rewritten to it; where none is, the file states the needed behaviour, marks it *To design* and lists it in its open items.
