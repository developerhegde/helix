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

B1 excludes:

- Reading real secrets, exchanging credentials, or authenticating to external systems.
- Contacting Jira, GitHub, Anypoint, Nexus, or a model provider.
- Building the webhook service, model gateway, agent sandbox, Maven proxy, or workflow engine.
- Storing client profiles or secrets in this repository.
- Reading, validating, importing, or depending on Meridian or any Meridian file. Helix is a standalone tool (owner decision, 2026-10-09).

## Profile boundary

A client profile is a directory outside the Helix repository and outside source control. It contains the Helix-owned `helix.yaml` file. The implementation may load only the profile path explicitly passed through `--profile` or `HELIX_CLIENT_PROFILE`; it must never search a home directory, repository tree, or environment for a profile.

Required directory shape:

```text
<client-profile>/
  helix.yaml
```

Helix reads no other file in the directory, including any `.env`. `helix.yaml` contains no secret value, and references a vault scope rather than a secret name or value.

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
  logging: core-logger-mdc
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
| B1-009 | Vault provider and scope are present; values are opaque references/scopes and contain no detected secret value. | error |
| B1-010 | Anypoint business group, connected-app reference, non-empty environment allowlist, and a parseable secret expiry are present. | error |
| B1-011 | No configured Anypoint environment is production-like. Reject case-insensitive `prod`, `production`, and names configured in the local policy table. | error |
| B1-012 | Connected-app expiry is in the future and within the warning horizon. Expired is an error; expiry within 30 days is a warning. | error / warning |
| B1-013 | Design defaults and each of the four gate-owner lists are present and non-empty. | error |
| B1-014 | The profile contains no plaintext secret based on key-name and value-shape detection. A finding must name the field path but never echo the value. | error |

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

1. **Standalone boundary:** Helix has no link to Meridian (owner decision, 2026-10-09). The former rule B1-015 (Meridian file parsing) is withdrawn and its id is not reused.
2. **Profile migration:** define only additive schema evolution until a migration command and rollback policy exist.
3. **Policy ownership:** the provider/residency policy table needs a named owner and release process before it can decide production eligibility.
4. **Secret detection:** detection is a tripwire, not proof of absence. It must remain conservative and never cause sensitive output.
