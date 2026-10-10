# Architecture decision — versioned client standards bundle

## Decision

Helix consumes client engineering standards through a **versioned standards bundle**, not live Confluence reads and not ad hoc documents attached per ticket.

A client may author standards in Confluence, SharePoint, or another document system. Before Helix uses them, a client architect or delegated standards owner exports and curates them into a machine-readable bundle in the client profile store. `helix.yaml` references the approved bundle version and SHA-256 digest. Every design bundle, generated Mule project, validation report, and pull request records that digest.

## Why now

This belongs in the design now, before the B2 project-generation contract. The standards bundle is the source of truth for how Helix should create Mule applications: naming grammar, project/POM baseline, API and error-handling conventions, allowed connectors, configuration layout, logging, MUnit expectations, and review requirements.

Without a versioned bundle, Helix either relies on model memory, reads mutable prose at run time, or embeds one client’s rules into product code. All three are unsuitable for a multi-client, auditable product.

## Boundary

### B1

- Defines the bundle reference in `helix.yaml`.
- Checks that the bundle is present, schema-valid, signed/approved, and digest-matched.
- Makes no live Confluence or document-system call.

### B2–B4

- Stages one immutable bundle version into each run.
- Builds design, project generation, and verification rules from it.
- Binds gate-two approval to the standards-bundle digest.

### Future document connectors

- A Confluence connector may export and propose a new bundle version.
- It never changes an active client profile or an in-flight run automatically.
- A named standards owner reviews and promotes the proposed bundle; Helix records the approval, version, and digest.

## Bundle shape

The initial format is `client_standards_bundle.v1`.

```yaml
schema: client_standards_bundle.v1
client_id: acme
version: 1.0.0
approved:
  by: client-architect@example.invalid
  at: 2026-10-09T10:00:00Z
source:
  system: confluence
  references:
    - id: ACME-MULE-STANDARDS
      revision: "42"
      exported_at: 2026-10-09T09:00:00Z
naming:
  contract_ref: naming_contract.v1
project:
  mule_runtime: 4.9.x
  java: 17
  golden_parent:
    group_id: example
    artifact_id: acme-mule-parent
    version: 1.0.0
  allowed_plugins: []
  forbidden_paths: [.github/**, .mvn/**, mvnw*]
api:
  default_contract: oas30
  contract_location: src/main/resources/api
  apikit: required
architecture:
  layer_policy: fewest_with_reuse
  allowed_layers: [process, system, experience]
connectors:
  allowed: []
  approval_required_for: []
configuration:
  property_policy_ref: validation_policy.v1
  environment_selector: env
logging:
  style: json_logger_module
  module: <org>-logger
  required_fields: [timestamp, level, appName, env, correlationId, flowName, message]
error_handling:
  required: [standard-error-handler, correlation-id]
testing:
  munit_version: 3.7.4
  require_concrete_assertions: true
  forbid_processor_under_test_mocks: true
  minimum_application_coverage: 80
review:
  required_artifacts: [contract, hld, lld, test_evidence]
  checklist: []
```

The schema remains deliberately narrow in its first iteration. Unknown prose must not be treated as executable policy.

## Converting prose into usable standards

The standards owner classifies each normative statement from the source documentation into one of these forms:

| Form | Helix behavior |
| --- | --- |
| Declarative setting | Direct bundle field, validated by schema. |
| Validation rule | Deterministic validator rule with an ID and pass/fail behavior. |
| Generation template | Versioned template or approved snippet with explicit inputs. |
| Decision table | Machine-readable condition/rationale/choice data. |
| Review checklist | Human gate requirement; not silently auto-enforced. |
| Guidance only | Staged as bounded reference text for the design agent; never treated as a mandatory rule. |

A standards item must have an identifier, source reference, classification, and approval status. The bundle must not contain unbounded ticket text, credentials, client secrets, or URLs that Helix will follow.

## Binding and change control

1. `helix.yaml` declares the bundle path, version, and digest.
2. `helix doctor` validates presence, schema, approval metadata, client ID, and digest.
3. The control plane writes the bundle digest into the B4 design bundle.
4. B2 project generation and `helix validate` refuse a design bundle whose standards digest differs from the staged bundle.
5. A standards update creates a new bundle version. It never alters an active ticket; a changed standard applies only after a new design run and gate-two approval.

## Recommended source flow

```text
Confluence / standards document
        ↓ export
Proposed client standards bundle
        ↓ client architect review and approval
Approved versioned bundle + SHA-256
        ↓ profile reference
Helix design, generation, validation, and PR evidence
```

This preserves Confluence as the authoring experience while making Helix runs reproducible and auditable.

## Information needed first

Provide one representative, sanitized standards document or page export—generic is sufficient. It should show the current rules for:

- Mule application naming and layers
- Mule runtime/JDK/MUnit/POM baseline
- API contract and APIkit conventions
- Configuration/property and secret handling
- Logging and error-handling conventions
- Connector/dependency restrictions
- Test, coverage, and review expectations

Helix will use it to create the first standards-bundle mapping and identify which items are deterministic rules versus architect review items.
