# B2 architecture decision — standalone naming and environment contract

## Decision

Helix owns client-specific application naming, environment mapping, and configuration-file naming. It does not inherit those concerns from Meridian.

Each client profile contains a versioned `naming` block in `helix.yaml`. Helix validates this block offline in B1, compiles it into an immutable `naming_contract.v1` input for each B2 attempt, and uses it for design generation, generated-project validation, pull-request metadata, and future deployment adapters.

The contract is declarative. Agents never invent names, environment suffixes, or configuration-file paths. They request names through Helix-owned deterministic functions; the design and verification stages parse generated names back against the same contract.

## Goals

- Preserve each client's naming grammar without requiring Meridian.
- Make every generated application, platform-object, branch, and configuration-file name deterministic and reversible.
- Enforce non-production scope during B1–B5.
- Keep naming data independent of Anypoint, Jira, GitHub, and model access.
- Give B2 validation an explicit source of truth for configuration-file locations and expected environments.
- Keep a future Meridian adapter possible, but optional.

## Non-goals

- Inferring a client's grammar from repositories or platform resources.
- Supporting arbitrary executable naming logic.
- Translating names from a future Meridian profile automatically.
- Defining deployment inventory, platform object creation, or production deployment behavior.

## Profile contract

`helix.yaml` gains the following block. It is client configuration, never generated from ticket text.

```yaml
naming:
  schema_version: 1
  application:
    separator: "-"
    repository:
      parts: [prefix, scope, region, name, layer, version]
    deployed:
      parts: [prefix, scope, region, name, layer, version, environment]
    allowed:
      prefix: [acme]
      scope: [src, run]
      region: [glb, euw]
      layer: [exp, prc, sys]
      version_pattern: "v[1-9][0-9]*"
      name_pattern: "[a-z][a-z0-9-]{1,48}"
  environments:
    - key: DEV
      suffix: dev
      order: 10
      production: false
    - key: SIT
      suffix: sit
      order: 20
      production: false
    - key: PROD
      suffix: prod
      order: 90
      production: true
  configuration:
    directory: src/main/resources/config
    base_file: config.yaml
    environment_file: config-{environment}.yaml
    secure_environment_file: config-secure-{environment}.yaml
    test_directory: src/test/resources/config
    test_file: config-munit.yaml
    secure_test_file: config-secure-munit.yaml
```

The example is illustrative. A client may use a different grammar, provided it satisfies the rules below.

## Canonical concepts

| Concept | Meaning |
| --- | --- |
| `repository_name` | The immutable source-repository/application identity, rendered from `application.repository.parts`. |
| `deployed_name` | The runtime identity for one environment, rendered from `application.deployed.parts`. |
| `environment key` | Stable internal identifier such as `DEV`; used in design bundles and validation reports. |
| `environment suffix` | Client-facing name segment such as `dev`; used only where the grammar includes `environment`. |
| `application parts` | Values for the configured parts: `prefix`, `scope`, `region`, `name`, `layer`, `version`, and optionally `environment`. |
| `configuration path` | A repository-relative path rendered from the `configuration` block, never supplied by an agent. |

## Grammar rules

### Application forms

1. `repository.parts` and `deployed.parts` each contain 2–8 unique parts.
2. Both forms must contain `name` and `version`.
3. `repository.parts` must not contain `environment`.
4. `deployed.parts` must contain `environment` when the client requires environment-specific runtime names; otherwise it must omit it for every environment.
5. `environment`, when present, is the final deployed-name part. This prevents ambiguous parsing.
6. Supported parts are `prefix`, `scope`, `region`, `name`, `layer`, `version`, and `environment`. Unknown parts are rejected.
7. `separator` is one printable, non-alphanumeric character and cannot be `/`, `\`, `.`, whitespace, `$`, `{`, or `}`.
8. Every fixed part except `name` and `version` has a non-empty allowlist. `name` and `version` are constrained by their configured regular expressions.
9. Values may not contain the separator, whitespace, path separators, placeholder syntax, or a control character.
10. Rendering joins normalized part values with the configured separator. Parsing splits the name and validates the exact part count and each part's constraint. Render-then-parse must reproduce the original part map exactly.

### Environment rules

1. Environment keys match `^[A-Z][A-Z0-9_]{1,31}$` and are unique.
2. Suffixes match `^[a-z][a-z0-9-]{0,31}$` and are unique.
3. `order` is a unique non-negative integer. Helix sorts environments by it.
4. At least two non-production environments are required for B2 because property validation compares environment-specific configuration.
5. B1–B5 reject any request, generated project target, or agent attempt that names an environment where `production: true`.
6. The profile can retain production definitions for naming completeness, but B1–B5 only compile `allowed_environments` from the non-production entries.

### Configuration-path rules

1. Every path is relative to the repository root and normalized with `/` separators.
2. `directory` and `test_directory` must be descendants of `src/main/resources/` and `src/test/resources/` respectively.
3. Paths may not contain `..`, an absolute-path prefix, variable expansion, or secret/marker syntax.
4. Environment configuration file templates must contain `{environment}` exactly once; base and test-file templates must not contain it.
5. Environment configuration paths are rendered using the **environment suffix**, not the environment key.
6. A normal and secure environment template must render different paths for every environment.
7. No generated configuration path may equal the API contract path, a design-document path, a Maven wrapper path, or a CI/workflow path.

## Helix-owned interface

`helix.naming` is a pure library with no network, filesystem, model, or environment-variable dependency.

| Function | Contract |
| --- | --- |
| `compile_contract(profile.naming) -> NamingContract` | Validates the block and returns an immutable, canonical contract with a SHA-256 digest. |
| `render_repository(parts) -> str` | Validates required parts and renders a repository name. |
| `render_deployed(parts, environment_key) -> str` | Renders a deployed name, resolving the environment suffix from the contract. |
| `parse_repository(value) -> Parts` | Parses and validates one repository name. |
| `parse_deployed(value) -> ParsedDeploymentName` | Parses and validates a deployed name, resolving its environment key from the suffix. |
| `configuration_paths(environment_key) -> ConfigurationPaths` | Returns base, environment, secure-environment, and test paths. |
| `allowed_environment_keys() -> tuple[str, ...]` | Returns only non-production environment keys, in order. |
| `is_production(environment_key) -> bool` | Returns the declared environment classification. |

`NamingContract` exposes no mutable dict. Every caller receives canonical values and the contract digest.

## Attempt input and evidence

The control plane compiles the profile's naming block before B2 begins and places this document in `naming-contract.json`:

```json
{
  "schema": "naming_contract.v1",
  "digest": "<sha256>",
  "application": {
    "separator": "-",
    "repository_parts": ["prefix", "scope", "region", "name", "layer", "version"],
    "deployed_parts": ["prefix", "scope", "region", "name", "layer", "version", "environment"]
  },
  "environments": [
    {"key": "DEV", "suffix": "dev", "order": 10, "production": false},
    {"key": "SIT", "suffix": "sit", "order": 20, "production": false}
  ],
  "configuration": {
    "base_path": "src/main/resources/config/config.yaml",
    "test_path": "src/test/resources/config/config-munit.yaml"
  }
}
```

The design bundle records:

- `naming_contract_digest`.
- The parts and rendered repository/deployed names for every application.
- The ordered non-production environment keys.
- The exact rendered configuration paths for every application and environment.

B2 validates the design bundle's digest against the staged contract before any project generation or Maven run. A profile change yields a different digest and requires the design to be regenerated and re-approved; Helix never silently applies a changed naming grammar to an approved design.

## B2 validation rules

The standalone validator introduced by `b2-standalone-mule-validation.md` adds these checks:

| ID | Rule | Outcome on failure |
| --- | --- | --- |
| NAM-001 | The staged `naming_contract.v1` validates and matches the design bundle digest. | `FAILED` — `NAMING_CONTRACT_MISMATCH` |
| NAM-002 | Every application repository name renders and parses under the contract. | `RETRY_BUILD` — `NAME_UNPARSED` |
| NAM-003 | Every deployed name renders and parses for every allowed non-production environment. | `RETRY_BUILD` — `DEPLOYED_NAME_UNPARSED` |
| NAM-004 | No B1–B5 artefact names a production environment. | `FAILED` — `PRODUCTION_ENVIRONMENT_REFUSED` |
| NAM-005 | Generated configuration files exist at the contract-rendered paths and nowhere else is used as a property source. | `RETRY_BUILD` — `CONFIGURATION_PATH_MISMATCH` |
| NAM-006 | Base and test configuration files are marker-free; environment and secure files contain markers only where the approved key list owes them. | `RETRY_BUILD` — `MARKER_POLICY_VIOLATION` |
| NAM-007 | Every generated application identifier is unique, case-insensitively, across the design bundle. | `RETRY_BUILD` — `APPLICATION_NAME_COLLISION` |

## Future Meridian adapter

A future optional `meridian_adapter` may translate a Meridian tenant profile into a proposed `naming_contract.v1` and compare its rendered names with Helix's contract. It may not:

- Change Helix's naming semantics at runtime.
- Add an implicit dependency to B1 or B2.
- Supply names to agents without Helix compiling and validating them first.
- Bypass the naming-contract digest bound to gate-two approval.

The adapter must declare its supported Meridian versions and pass contract tests against each pinned version.

## Acceptance criteria

This design is ready when the implementation can prove:

1. Two synthetic client contracts render different valid names for the same logical application and reject each other's names.
2. Every rendered repository and deployed name round-trips to the identical parts and environment key.
3. Production environment keys are rejected in B1–B5 project generation and verification.
4. Configuration paths render deterministically, stay inside allowed resource directories, and cannot collide.
5. A changed naming contract invalidates a design bundle before build begins.
6. No agent, ticket, design prose, or external-system response can choose a raw filesystem path or bypass the contract.
7. The complete naming subsystem runs offline and has no Meridian, Anypoint, Jira, GitHub, or model dependency.

## Required LLD reconciliation

Before B2 implementation, replace Meridian-dependent naming and environment sections in the LLD with this contract:

- `00-conventions.md`: schema ownership and environment/name identifiers.
- `02-client-profile-and-doctor.md`: profile schema and B1 validation.
- `04-agent-runtime.md`: naming tools call `helix.naming`, not Meridian.
- `06-b4-design.md`: design renders and parses names through `NamingContract`.
- `07-b2-build-test-pr.md`: property file generation and validation use `configuration_paths()`.
- `08-b5-orchestration.md`: profile digest and naming-contract digest are checked at phase boundaries.
- `10-security-and-test-plan.md`: fixture grammars and standalone naming guards.
