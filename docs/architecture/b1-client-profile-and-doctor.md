# B1 implementation contract — client profile and `helix doctor`

## Purpose

B1 establishes the tenant boundary that every Helix phase consumes. It delivers a versioned, non-secret client-profile contract and a deterministic `helix doctor` command that validates profile completeness and prerequisite readiness without contacting an agent, a model, Jira, GitHub, or Anypoint.

This is a design contract for the Build → Test → Refactor stream. It does not prescribe the programming language, CLI framework, or persistence technology; those choices must be documented by the implementation team and remain replaceable behind the CLI and schema contracts below.

## Scope

B1 includes:

- A schema-versioned client profile.
- A loader that validates the profile before any phase starts.
- A `helix doctor --profile <path>` command.
- Machine-readable and human-readable doctor results.
- Synthetic fixture profiles and automated validation tests.
- A documented prerequisite register for external onboarding items.
- Offline validation of the profile's naming block and of the client standards bundle it references.

B1 excludes:

- Reading real secrets, exchanging credentials, or authenticating to external systems.
- Contacting Jira, GitHub, Anypoint, Nexus, or a model provider.
- Building the webhook service, model gateway, agent sandbox, Maven proxy, or workflow engine.
- Storing client profiles or secrets in this repository.
- Reading, validating, importing, or depending on Meridian or any Meridian file. Helix is a standalone tool (owner decision, 2026-10-09).

## Profile boundary

A client profile is a directory outside the Helix repository and outside source control. It contains the Helix-owned `helix.yaml` file and the client standards bundle that file references. The implementation may load only the profile path explicitly passed through `--profile` or `HELIX_CLIENT_PROFILE`; it must never search a home directory, repository tree, or environment for a profile.

Required directory shape:

```text
<client-profile>/
  helix.yaml
  standards/
    bundle.yaml        # client_standards_bundle.v1, at the path helix.yaml names
```

Helix reads `helix.yaml` and the one standards bundle it references, and no other file in the directory, including any `.env`. `helix.yaml` contains no secret value, and references a vault scope rather than a secret name or value.

## `helix.yaml` contract, version 1

```yaml
schema_version: 1
client_id: acme
model_route:
  provider: anthropic # anthropic | bedrock | vertex
  region: eu-west-1
  phases:
    intake: claude-haiku
    design: claude-sonnet
    build: claude-sonnet
    test: claude-sonnet
  run_cap_usd: 170
  phase_cap_usd: 85
data_handling:
  permitted_regions:
    - eu-west-1
  zero_data_retention_required: true
  allowed_hosts:
    - api.anthropic.com
jira:
  cloud_id: example-cloud-id
  project_key: ACME
  webhook_secret_ref: vault://helix/acme/jira-webhook
  bot_account_id: helix-jira-bot
  statuses:
    needs_info: Needs info
    requirement_review: Requirement review
    design_review: Design review
github:
  organisation: acme
  bot_account: helix-github-bot
  allowed_bots:
    - helix-jira-bot
    - helix-github-bot
  repositories:
    - integration-services
vault:
  provider: ci-secret-store
  scope: helix/acme
anypoint:
  business_group_id: acme-nonprod
  connected_app_ref: vault://helix/acme/anypoint-connected-app
  secret_expiry: 2027-01-01T00:00:00Z
  environments:
    - sandbox
    - test
design:
  contract_format: oas3
  governance_ruleset: anypoint-best-practices-1.6.5
  logging: json-logger-module
naming:                       # full grammar and rules: b2-naming-and-environment-contract.md
  schema_version: 1
  application:
    separator: "-"
    repository: {parts: [prefix, scope, region, name, layer, version]}
    deployed: {parts: [prefix, scope, region, name, layer, version, environment]}
    allowed: {prefix: [acme], scope: [src, run], region: [glb, euw], layer: [exp, prc, sys]}
    version_pattern: "v[1-9][0-9]*"
    name_pattern: "[a-z][a-z0-9-]{1,48}"
  environments:
    - {key: DEV, suffix: dev, order: 10, production: false, platform_name: sandbox}
    - {key: SIT, suffix: sit, order: 20, production: false, platform_name: test}
  configuration:
    directory: src/main/resources/config
    base_file: config.yaml
    environment_file: config-{environment}.yaml
    secure_environment_file: config-secure-{environment}.yaml
    test_directory: src/test/resources/config
    test_file: config-munit.yaml
    secure_test_file: config-secure-munit.yaml
standards:                    # client-standards-bundle.md
  path: standards/bundle.yaml
  version: 1.0.0
  sha256: <64 lowercase hexadecimal characters>
gates:
  requirement:
    - architect@example.invalid
  design:
    - architect@example.invalid
  merge:
    - developer@example.invalid
  deploy:
    - release-owner@example.invalid
```

## Validation rules

The loader and doctor must apply the following rules in stable order. Each failed rule returns its identifier, severity, profile path, and remediation text. The doctor reports all independent failures in one run.

| ID | Rule | Severity |
| --- | --- | --- |
| B1-001 | `helix.yaml` exists and is a regular file. | error |
| B1-002 | `helix.yaml` parses and has `schema_version: 1`. | error |
| B1-003 | `client_id` is present and matches `^[a-z0-9]+(?:-[a-z0-9]+)*$`. | error |
| B1-004 | Model provider, region, phase models, run cap, and phase cap are present; all caps are positive and the phase cap does not exceed the run cap. | error |
| B1-005 | The model route complies with data-handling rules: its region is permitted, and the configured provider is compatible with any zero-data-retention requirement. Compatibility is evaluated from a versioned local policy table, not model prompt text. | error |
| B1-006 | `allowed_hosts` is non-empty, contains only valid HTTPS host names, and includes only hosts approved by the client's policy. | error |
| B1-007 | Jira cloud, project, bot identity, webhook secret reference, and the three lifecycle statuses are present. | error |
| B1-008 | GitHub organisation, bot identity, non-empty repository onboarding list, and `allowed_bots` containing both configured bot identities are present. | error |
| B1-009 | Vault provider and scope are present; values are opaque references/scopes and contain no detected secret value. Every `vault://` reference in the profile names a secret inside `vault.scope`, with no `.` or `..` segment. | error |
| B1-010 | Anypoint business group, connected-app reference, non-empty environment allowlist, and a parseable secret expiry are present. | error |
| B1-011 | No configured Anypoint environment is production-like. Reject case-insensitive `prod`, `production`, and names configured in the local policy table. | error |
| B1-012 | Connected-app expiry is in the future and within the warning horizon. Expired is an error; expiry within 30 days is a warning. | error / warning |
| B1-013 | Design defaults and each of the four gate-owner lists are present and non-empty. | error |
| B1-014 | The profile contains no plaintext secret based on key-name and value-shape detection. A finding must name the field path but never echo the value. | error |
| B1-015 | The `naming` block compiles to a valid `naming_contract.v1` under the grammar, environment and configuration-path rules of `b2-naming-and-environment-contract.md`, with at least two non-production environments. | error |
| B1-016 | The `standards` reference names a safe relative path inside the profile directory, and the file there is a `client_standards_bundle.v1` whose SHA-256, version and `client_id` match the profile and which carries approval metadata. Every file the bundle lists under `files[]` exists beside it with the stated digest and a known purpose. | error |
| B1-017 | `client_id` equals the name of the profile directory. | error |
| B1-018 | Every top-level key is part of the schema. An unknown key is reported and ignored, so the schema can grow by addition while a misspelt key is still seen. | warning |
| B1-019 | Where the profile and the standards bundle state the same fact, they agree: the `design` block's contract format and logging style, and the naming block's configuration layout. The bundle is the source. | error |
| B1-020 | A naming environment's optional `platform_name` is listed under `anypoint.environments` when the environment is non-production, and is not listed when it is production. | error |

The implementation must define a local, versioned policy table for provider/residency compatibility and production-like environment aliases. It must record the policy-table version in doctor output.

## `helix doctor` interface

```text
helix doctor --profile <absolute-path> [--format text|json] [--strict]
```

- `--profile` is required and must be an absolute path.
- `--format text` is the default and is concise for operators.
- `--format json` returns a stable object for automation.
- `--strict` upgrades warnings to a non-zero exit but does not hide the complete result set.
- The command is offline and read-only. It must not load `.env` into the process environment, resolve vault references, make network calls, or print secret-shaped content.

Exit codes:

| Exit | Meaning |
| --- | --- |
| 0 | Healthy; no errors, and no warnings when `--strict` is used. |
| 1 | Findings; warnings only without `--strict`, or errors with any mode. |
| 2 | Operational failure; invalid invocation, unreadable profile path, unsupported format, or an internal failure. |

JSON result contract:

```json
{
  "schema_version": 1,
  "client_id": "acme",
  "policy_version": "1",
  "status": "healthy",
  "findings": [
    {
      "id": "B1-012",
      "severity": "warning",
      "path": "anypoint.secret_expiry",
      "message": "Connected-app secret expires within 30 days.",
      "remediation": "Rotate the connected-app secret and update its expiry metadata."
    }
  ]
}
```

## Test contract

Claude Code must implement automated tests for:

1. A complete synthetic profile returning healthy.
2. A missing `helix.yaml` producing B1-001.
3. Each required `helix.yaml` section omitted independently.
4. Production-like environments rejected, including casing variants.
5. Expired, soon-to-expire, and sufficiently future expiries.
6. A forbidden model-route/residency combination rejected through the local policy table.
7. A plaintext-secret fixture failing without echoing the secret in text or JSON output.
8. `allowed_bots` missing either configured bot identity.
9. Invalid run/phase caps and a phase cap exceeding the run cap.
10. Text and JSON output stability, including exit-code semantics and `--strict`.
11. Proof that doctor makes no network call, does not resolve a vault reference, and does not import `.env` values into its process environment.
12. A missing or invalid naming block, and one with fewer than two non-production environments, producing B1-015.
13. A standards bundle that is missing, has a different digest, names another client or version, lacks approval metadata, or sits at a path outside the profile directory, producing B1-016.
14. A profile directory whose name differs from `client_id` producing B1-017, and an unknown top-level key producing a B1-018 warning that fails only under `--strict`.
15. A `vault://` reference outside `vault.scope`, including one that climbs out with `..`, producing B1-009.
16. A `design` value or a configuration layout that differs from the standards bundle producing B1-019, and a differently spelt but equal value passing.
17. A platform name missing from `anypoint.environments`, and a production environment's platform name present in it, producing B1-020.
18. A bundle-listed file that is missing, has another digest, has an unknown purpose, or sits outside the bundle's directory, producing B1-016.

Fixtures must use only synthetic `acme-*` values. No real tenant names, account identifiers, URLs, emails, tokens, or secrets may enter the repository.

## Acceptance criteria

B1 is complete when:

- `helix doctor` validates a complete synthetic profile and reports every independent defect in an invalid fixture.
- The CLI is offline, read-only, deterministic, and safe to run in CI.
- Connected-system checks for the vault, Jira, GitHub, Anypoint, Nexus, and the model route remain deferred to the B2 readiness implementation; B1 must not simulate those checks as complete.
- The profile schema and output contracts are versioned and covered by tests.
- The doctor refuses production-like environments and expired connected-app metadata.
- The implementation has no embedded client data or credentials.
- The B1 spike and real external onboarding items remain recorded as pending; they are not simulated as complete by this command.

## Architectural challenges to resolve during implementation

1. **Standalone boundary:** Helix has no link to Meridian in B1 (owner decision, 2026-10-09). The Meridian file check that first held the id B1-015 was withdrawn before any release; B1-015 now identifies the naming rule. A future integration must enter through an explicit, version-pinned adapter contract and an opt-in profile capability; it must not become an implicit B1 dependency.
2. **Profile migration:** define only additive schema evolution until a migration command and rollback policy exist.
3. **Policy ownership:** the provider/residency policy table needs a named owner and release process before it can decide production eligibility.
4. **Secret detection:** detection is a tripwire, not proof of absence. It must remain conservative and never cause sensitive output.
