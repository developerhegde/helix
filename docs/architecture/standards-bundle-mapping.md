# Standards bundle mapping

**Source:** `docs/mulesoft-development-standards.md`, version 1.1 (2026-10-09).
**Status:** On 2026-10-12 the owner accepted this classification and decided D1 to D5 as recommended. A rule becomes active when its check is built and the bundle's `rules[]` lists it.

This document turns every rule of the standards document into one entry, as `client-standards-bundle.md` requires: an identifier, its source section, its form, and who checks it.

## How to read the tables

| Column | Values |
| --- | --- |
| **S** (strength) | **B** Blocking, **A** Advisory, as the standards document states |
| **Form** | *Setting* (a bundle field), *Validation* (a pass/fail check), *Template* (Helix writes the file or text), *Decision table* (machine-readable choices), *Checklist* (a person confirms it), *Guidance* (reference text only) |
| **Checked by** | *Helix* (automatic), *Reviewer* (a person at a gate or in the pull request), *Client* (the client's pipeline or platform, outside Helix in B1–B5) |
| **Status** | *Built* (code enforces it today), *Partly built*, *Designed* (in a contract or the LLD, not built), *To design* (no design yet), *Reviewer*, *Outside Helix*, *Deviation* (accepted for B2) |

## Decisions (made 2026-10-12)

| # | Conflict between the standards and the current Helix design | Rules | Decision |
| --- | --- | --- | --- |
| D1 | **Configuration layout.** The standards keep one `config.yaml` with a default for every property and one `config-secure.yaml`; environment values are deployment properties supplied by the pipeline. Helix's design packages a `config-{environment}.yaml` and `config-secure-{environment}.yaml` per environment inside the application, with marks. | STD-CFG-01 to 03 | Add `configuration.layout` to the bundle with two values, `deployment_properties` and `environment_files`. This client's standard is `deployment_properties`; the naming contract and LLD 07 §3.4.4 then need that second mode. |
| D2 | **API specification location.** The standards consume the specification from Exchange as a dependency and forbid a copy under `src/main/resources/api`. Helix's design commits the contract into that folder and checks its digest there. | STD-POM-07, STD-API-01 | Add `api.contract_source` with `repository` and `exchange_dependency`. Keep `repository` for B2, because publishing to Exchange needs platform access that B1–B5 do not have; record the deviation in the pull request. |
| D3 | **Mule file names.** The standards name the files `global.xml`, `<name>-api.xml`, `<resource>-impl.xml` and `error-handler.xml`. LLD 07 renders `global-config.xml`. | STD-NAM-05 | Helix follows the standard: file names come from the bundle's `project.mule_files`. |
| D4 | **Branch name.** The standards require `feature/<ticket>-<slug>`. Helix's branch is `helix/{ticket_key}` (LLD 00 §6). | STD-NAM-18 | Take the pattern from the bundle's `review.branch_pattern`; default to the client's. |
| D5 | **Same keys in every environment.** The standards require identical key sets. Helix lets a key list only some environments. | STD-CFG-02 | Add `configuration.same_keys_every_environment: true`; the validator then refuses a key that omits an environment. Folded into D1 if `deployment_properties` is chosen. |

## Summary

| Status | Rules |
| --- | --- |
| Built | 5 |
| Partly built | 7 |
| Designed | 14 |
| To design | 45 |
| Reviewer | 16 |
| Outside Helix | 6 |
| Deviation | 1 |
| **Total** | **94** |

Of the 94 rules (87 Blocking, 7 Advisory), 71 are for Helix to check automatically, 16 stay with a reviewer, 6 belong to the client's pipeline or platform, and 1 is an accepted deviation in B2. Only 12 of the 71 are fully or partly built today.

## Naming

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-NAM-01 | Repository and `artifactId` are `<domain>-<layer>-v<major>`; layer is `exp`, `prc` or `sys` | B | Setting: profile `naming` block, parts `name`, `layer`, `version` | Helix | Built: B1-015 checks the grammar and NAM-002 the project's names |
| STD-NAM-02 | Exchange specification asset is `<domain>-<layer>-api`, title spells the layer | B | Template | Helix | To design |
| STD-NAM-03 | Runtime application is `<artifactId>-<env>` | B | Setting: deployed parts end in `environment` | Helix | Built (NAM-003) |
| STD-NAM-04 | API base path is `/api/v<major>/<resource>` | B | Validation | Helix | To design |
| STD-NAM-05 | Mule files are `global.xml`, `<name>-api.xml`, `<resource>-impl.xml`, `error-handler.xml` | B | Setting and Template | Helix | To design (D3: Helix follows the standard) |
| STD-NAM-06 | APIkit flows keep their generated names | B | Validation: one flow per contract operation, name unchanged | Helix | Designed |
| STD-NAM-07 | Implementation flow is `<verb>-<resource>-flow` | B | Validation: pattern | Helix | To design |
| STD-NAM-08 | Sub-flow is `<action>-<object>-subflow` | B | Validation: pattern | Helix | To design |
| STD-NAM-09 | Connector configuration is `<system>-<connector>-config`; the listener is `http-listener-config` | B | Validation: pattern | Helix | To design |
| STD-NAM-10 | Property key is a lowercase dot path; secrets are read as `${secure::<key>}` | B | Validation | Helix | Partly built: the secure reference is checked; the key pattern is not |
| STD-NAM-11 | Flow variables are camelCase | B | Validation: pattern | Helix | To design |
| STD-NAM-12 | DataWeave script is `dwl/<resource>/<purpose>.dwl`, kebab-case | B | Validation: path pattern | Helix | To design |
| STD-NAM-13 | DataWeave module is `modules/<Module>.dwl` | B | Validation: path pattern | Helix | To design |
| STD-NAM-14 | Custom error type is `APP:<UPPER_SNAKE_REASON>` | B | Validation: pattern | Helix | To design |
| STD-NAM-15 | MQ destination is `<domain>-<event>-<env>`; dead-letter queue is `dlq-<queue>` | B | Setting and Template | Helix | To design |
| STD-NAM-16 | Object Store is `<purpose>-os` | B | Validation: pattern | Helix | To design |
| STD-NAM-17 | API Manager client application is `<consumer>-<env>` | B | Guidance | Client | Outside Helix |
| STD-NAM-18 | Branch is `feature/…`, `bugfix/…`, `hotfix/…` or `release/<semver>` | B | Setting | Helix | To design (D4: the pattern comes from the bundle) |
| STD-NAM-19 | Commit message is `<TICKET>: imperative summary`, at most 72 characters | B | Template | Helix | To design |
| STD-NAM-20 | Kebab-case everywhere except modules, flow variables and error reasons | B | Validation: covered by 07 to 14 | Helix | To design |
| STD-NAM-21 | No environment token in a repository, Exchange asset or `artifactId` | B | Validation | Helix | Built: the naming contract refuses `environment` in the repository form |
| STD-NAM-22 | A new major version is a new repository and `artifactId` | B | Checklist, at the design gate | Reviewer | Reviewer |
| STD-NAM-23 | APIkit flow names are never changed | B | Validation: same check as 06 | Helix | Designed |
| STD-NAM-24 | Every processor has an intent-based `doc:name` | A | Checklist | Reviewer | Reviewer |

## POM, runtime and dependencies

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-POM-01 | Inherit the approved parent POM; the child holds only application-specific content | B | Setting `project.golden_parent` and Validation | Helix | Partly built: parent, repositories and plugins are checked; versions in the child are not |
| STD-POM-02 | Mule 4.9 LTS and Java 17 | B | Setting and Validation | Helix | Partly built: the runtime is checked; Java is not |
| STD-POM-03 | Plugin, connector, library and coverage versions are pinned in the parent | B | Validation: the child declares no version | Helix | To design |
| STD-POM-04 | `groupId` is the organisation or business-group ID; semantic versioning | B | Setting and Validation | Helix | To design |
| STD-POM-05 | No version ranges, `LATEST` or `RELEASE` | B | Validation | Helix | To design |
| STD-POM-06 | Approved connectors and shared libraries only | B | Setting `connectors.allowed` and Validation | Helix | To design |
| STD-POM-07 | The API specification comes from Exchange as a dependency, never copied into the project | B | Setting | Helix | Deviation (D2: in B2 the contract stays in the project and the pull request records it) |
| STD-POM-08 | JDBC drivers and similar JARs go through `sharedLibraries` | B | Validation | Helix | To design |
| STD-POM-09 | Test-only dependencies have test scope; unused dependencies are removed | A | Checklist | Reviewer | Reviewer |
| STD-POM-10 | `mule-artifact.json` declares the minimum Mule version, Java 17 and every secure property | B | Template and Validation | Helix | To design |

## Build and deployment

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-BLD-01 | Shared environments are deployed only through the pipeline | B | Guidance | Client | Outside Helix (deployment is B6) |
| STD-BLD-02 | Pipeline variables set environment, name and sizing; no per-environment Maven profiles | B | Validation: no `profiles` in the child POM | Helix | To design |
| STD-BLD-03 | Platform credentials never appear in a POM | B | Validation: secret scan | Helix | Designed (LLD 07 §3.4.5) |
| STD-BLD-04 | `finalName` is not overridden | B | Validation | Helix | To design |
| STD-BLD-05 | Tests run before packaging | A | Template: verify stage order | Helix | Designed (LLD 07 §3.6) |

## APIkit and API design

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-API-01 | A RAML 1.0 or OAS 3.0 specification is designed and published before implementation | B | Setting `api.default_contract`; the design gate | Helix and Reviewer | Designed (D2: gate two approves the contract held in the repository) |
| STD-API-02 | The specification passes the Anypoint Best Practices ruleset with no violation | B | Validation, in the design phase | Helix | Designed (LLD 06) |
| STD-API-03 | Reuse the organisation's Exchange fragments; no local copy | B | Setting: fragment list; Checklist | Reviewer | Reviewer |
| STD-API-04 | Plural nouns, path and query parameter use, camelCase fields, ISO-8601 UTC times, currency codes, documented responses | B | Validation where the ruleset covers it; Checklist for the rest | Helix and Reviewer | Designed |
| STD-API-05 | One APIkit router; generated flows only delegate; request validation stays on | B | Validation | Helix | To design |
| STD-API-06 | Console state, base path, correlation ID, autodiscovery and APIkit error mapping come from properties and the global configuration | B | Template and Validation | Helix | To design |

## Configuration and secrets

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-CFG-01 | `config.yaml` holds a default for every property | B | Setting | Helix | To design (D1: `deployment_properties` layout) |
| STD-CFG-02 | Environment values are deployment properties from the pipeline; every environment has the same keys | B | Setting | Helix | To design (D1 and D5: `deployment_properties` layout) |
| STD-CFG-03 | Secrets live in `config-secure.yaml` and are read as `${secure::<key>}` | B | Setting | Helix | To design (D1: `deployment_properties` layout) |
| STD-CFG-04 | No hard-coded host, port, path, credential, timeout, pool size, cron, queue or flag | B | Validation: literal scan | Helix | Designed (LLD 07, `LITERAL_CONFIG_VALUE`) |
| STD-CFG-05 | Feature flags are `feature.<name>.enabled`, default `false` | A | Validation: pattern | Helix | To design |
| STD-CFG-06 | API Manager resources and queues are created by the pipeline; `api.id` is captured | A | Guidance | Client | Outside Helix |
| STD-SEC-01 | The real `secure.key` never appears in a file, POM, log or test resource | B | Validation: it is a deployment property, defined in no file | Helix | Built |
| STD-SEC-02 | A dummy `secure.key` exists only in the parent POM's test configuration | B | Setting | Helix | Designed |
| STD-SEC-03 | Every secret is encrypted and read only as `${secure::<key>}` | B | Validation | Helix | Built |
| STD-SEC-04 | A plaintext secret anywhere is Blocking and is rotated the same day | B | Validation; rotation is the client's | Helix and Client | Partly built: configuration files are scanned; history is designed |
| STD-SEC-05 | One encryption key per environment, in the secret store | B | Guidance | Client | Outside Helix |
| STD-SEC-06 | `secureProperties` lists every secure property and `secure.key` | B | Template and Validation | Helix | To design |
| STD-SEC-07 | Private keys for UAT and production are never committed; truststores may be | B | Validation: forbidden file types | Helix | To design |
| STD-SEC-08 | Local defaults and test overrides hold synthetic credentials only | B | Validation: fixture allowlist | Helix | Designed |
| STD-SEC-09 | `settings.xml`, `.env`, `*.key` and local overrides are ignored by Git | B | Template | Helix | To design |

## Logging and error handling

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-LOG-01 | JSON logging through the organisation's module or one `log-event` sub-flow; no free-text `<logger>` | B | Setting `logging.style`, `logging.module`; Validation | Helix | Partly built: B1-016 requires the setting; the project is not scanned |
| STD-LOG-02 | Each event carries the required fields | B | Setting `logging.required_fields`; Template | Helix | Partly built: the setting exists; nothing checks the project |
| STD-LOG-03 | Log request receipt, each outbound call, completion and handled errors | B | Checklist | Reviewer | Reviewer |
| STD-LOG-04 | Production level is INFO; DEBUG only in dev and test; no TRACE | B | Validation, on `log4j2.xml` | Helix | To design |
| STD-LOG-05 | Never log secrets, authorisation headers, personal data or unmasked payloads | B | Checklist | Reviewer | Reviewer |
| STD-LOG-06 | Keep Mule's correlation ID; adopt and forward `x-correlation-id` | B | Checklist | Reviewer | Reviewer |
| STD-ERR-01 | One global error handler in `error-handler.xml`; flows define none of their own | B | Validation | Helix | To design |
| STD-ERR-02 | `on-error-propagate` by default; a continue path needs a fallback, named types, a WARN log and a reason | B | Validation: no continue on `ANY`; Checklist for the reason | Helix and Reviewer | To design |
| STD-ERR-03 | Business errors are `APP:<REASON>`; connector errors are translated at the boundary | B | Checklist | Reviewer | Reviewer |
| STD-ERR-04 | Retry only idempotent operations; retry settings come from properties | B | Checklist | Reviewer | Reviewer |
| STD-ERR-05 | Event-driven failures reach nack or dead-letter handling | B | Checklist | Reviewer | Reviewer |
| STD-ERR-06 | Every error branch sets the HTTP status and renders the shared envelope | B | Template: shared script | Helix | To design |
| STD-ERR-07 | The error envelope has the fixed shape | B | Template | Helix | To design |
| STD-ERR-08 | Error types map to HTTP status and consumer code as tabled | B | Decision table `error_handling.mappings` | Helix | To design |

## Connectors

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-CON-01 | Approved connectors only, each configured once in the global file | B | Setting and Validation | Helix | To design |
| STD-CON-02 | Host, port, path, credentials, timeout and reconnection come from properties | B | Validation | Helix | To design |
| STD-CON-03 | HTTP requests have explicit timeouts and keep standard response validation | B | Validation | Helix | To design |
| STD-CON-04 | Database: parameterised queries, explicit columns, pooling, timeouts | B | Checklist | Reviewer | Reviewer |
| STD-CON-05 | MQ: manual acknowledgement, dead-letter queue, redelivery limit, idempotency, correlation ID | B | Checklist | Reviewer | Reviewer |
| STD-CON-06 | File, SFTP, Salesforce, Object Store, Scheduler and Web Service Consumer follow their documented requirements | B | Guidance | Reviewer | Reviewer: the Markdown text is too general to check; the Word file's per-connector table is needed to write rules |

## MUnit and coverage

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-TST-01 | One suite per implementation file in `src/test/munit/`, with behaviour, execution and validation sections | B | Validation | Helix | To design |
| STD-TST-02 | Every external system is mocked by `doc:name`; the flow under test, transforms and the router are never mocked | B | Validation | Helix | Designed (LLD 07 §3.5.2) |
| STD-TST-03 | Tests cover scripts, validations, raised errors, the global handler, operations and acknowledgement paths | B | Validation for mappings; Checklist for the rest | Helix and Reviewer | Designed |
| STD-TST-04 | Tests are independent, never sleep, clear state, and ignore nothing without a ticket | B | Validation | Helix | To design |
| STD-TST-05 | Test resources hold synthetic data only | B | Validation: fixture allowlist | Helix | Designed |
| STD-TST-06 | The build fails below 75% application, 50% resource and 50% flow coverage | B | Setting and Validation | Helix | Partly built: application coverage is checked; resource and flow are not in the evidence |
| STD-TST-07 | A new coverage exclusion needs a reason and approval; APIkit flows are never excluded | B | Validation: the child POM declares no exclusion | Helix | To design |
| STD-TST-08 | Coverage reports are published as artefacts | A | Guidance | Client | Outside Helix |

## Pull-request review

| ID | Rule | S | Form | Checked by | Status |
| --- | --- | --- | --- | --- | --- |
| STD-REV-01 | Protected branches need a non-author approval; two for a hotfix to production | B | Setting `review.approvals`; repository settings | Client | Outside Helix; the doctor's approval proof is designed (LLD 07 §3.8.8) |
| STD-REV-02 | Build, tests, coverage, secret scan and static checks pass before review | B | Template: a draft pull request until evidence is green | Helix | Designed (LLD 07 §3.8.4) |
| STD-REV-03 | Every Blocking finding is fixed | B | Checklist | Reviewer | Reviewer |
| STD-REV-04 | A reviewer cannot downgrade a Blocking finding; exceptions are recorded | B | Checklist | Reviewer | Reviewer |
| STD-REV-05 | A merge to main bumps the version and updates the changelog | B | Template | Helix | To design |
| STD-REV-06 | First response within one business day; about 400 changed lines | A | Guidance | Reviewer | Reviewer |

## Next

1. Design the `deployment_properties` layout (D1) in the naming contract and LLD 07 §3.4.4, and carry the branch pattern (D4) through LLD 01, 02, 03, 06 and 07, which still assume the old branch name.
2. Add the approved rules to the bundle as its `rules[]` registry, each with this document's identifier.
3. Design the 40 *To design* rules as validator checks, starting with the POM and naming patterns, which need no new input.
4. Regenerate the `acme-a` fixture bundle and its digest.
