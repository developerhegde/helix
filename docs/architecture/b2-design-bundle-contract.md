# B2 architecture decision — design bundle contract (`design_bundle.v1`)

## Decision

`design_bundle.v1` is the only description of the approved design that B2 reads. B4 writes it, gate two approves its exact bytes, and it never changes afterwards. B2 generation and `helix validate` take the design from this file and from nothing else: not the ticket, not design prose, not a model's memory.

LLD `06-b4-design.md` §3.13 owns the full schema. This contract fixes the part B2 depends on, adds the two bindings the standalone design needs, and lists the fields whose source changed when Helix stopped relying on Meridian. 06 must carry every field below under the same name.

## Fields B2 reads

| Field | Shape | B2 rule | Failure code |
| --- | --- | --- | --- |
| `schema` | `"design_bundle.v1"` | Must match. | `DESIGN_BUNDLE_INVALID` |
| `status` | `complete` or `needs_choice` | B2 runs only on `complete`. | `INPUT_INCOMPLETE` |
| The file's SHA-256 | — | Equals the digest gate two approved. The bundle carries no digest of itself. | LLD 07, step S1 |
| `standards_bundle_digest` | 64 lowercase hexadecimal characters | **New.** Equals the SHA-256 of the staged `client_standards_bundle.v1`. | `STANDARDS_BUNDLE_MISMATCH` |
| `naming_contract_digest` | 64 lowercase hexadecimal characters | **New.** Equals the digest of the staged `naming_contract.v1`. | `NAMING_CONTRACT_MISMATCH` |
| `environments[]` | Environment keys | **Changed source.** The naming contract's non-production keys, in its `order`; at least two; never a production key. | `INPUT_INCOMPLETE`, `PRODUCTION_ENVIRONMENT_REFUSED` |
| `applications[]` | `{role, layer, primary, repository_name, parts {}, deployed_names {ENV: name}, configuration_paths {ENV: {environment, secure_environment}}}` | Exactly one `primary`. Every name renders from `parts` and parses back under the contract; names are unique without regard to case; paths equal `configuration_paths(ENV)`. | `NAME_UNPARSED`, `DEPLOYED_NAME_UNPARSED`, `APPLICATION_NAME_COLLISION`, `CONFIGURATION_PATH_MISMATCH` |
| `repo_name` | string | Equals the primary application's `repository_name`. | `NAME_UNPARSED` |
| `contract` | `{format, path, sha256, operations[]}`, or `{format: none}` | The file at `path` has that digest; every operation has a generated flow. | `DESIGN_ARTEFACT_CHANGED` |
| `documents.hld`, `documents.lld` | `{path, sha256}` | The file at `path` has that digest. | `DESIGN_ARTEFACT_CHANGED` |
| `keys[]` | `{key, class, type, environments[], value, fixture, config_file {}}` | The whole property design: see *Key classes*. | `PROPERTY_UNDEFINED`, `PROPERTY_UNUSED`, `MARKER_POLICY_VIOLATION` |
| `deployment_property_keys[]` | string[] | Exactly the keys of class `deployment`. Declared, never written to a file. | `DEPLOYMENT_PROPERTY_WRITTEN` |
| `mappings[]` | `{id, …}` with `id` matching `^MAP-[0-9]{3,}$` | Every id is anchored in DataWeave as `// map:MAP-nnn`. | `MAPPING_ANCHOR_MISSING` |

A bundle without `contract`, `documents`, `keys`, `deployment_property_keys` or `mappings` is refused before any other check.

## Key classes

| `class` | Written to | Value in the file | Who supplies the real value |
| --- | --- | --- | --- |
| `invariant` | The base file | The bundle's `value` | Nobody: it is the same everywhere |
| `env_specific` | The environment file of each environment in `environments[]` | `${HELIX_SET_<ENV>}` | The key holder, after merge |
| `secret` | The secure environment file of each environment in `environments[]` | `${HELIX_ENCRYPT_<ENV>}` | The key holder, after merge, encrypted |
| `deployment` | No file | — | The deployment pipeline; listed in the pull request |

The validator proves `keys[]` against the generated source: every key the code reads is defined in a generated file or declared for deployment, and every approved key is read.

## Binding and integrity

1. The bundle is written as canonical JSON. Gate two binds to the SHA-256 of its bytes.
2. Before any generation or Maven run, B2 checks in this order: schema, gate-two digest, standards digest, naming digest, then the digest of each member file (contract, HLD, LLD).
3. A change to the profile's naming block or to the standards bundle gives a different digest. The design is then regenerated and approved again; an approved design is never re-read under changed rules.

## What changed from the earlier design

| Field | Before | Now |
| --- | --- | --- |
| `environments[]` | Ordered by Meridian's environment ranking | Ordered by the naming contract |
| `applications[]` names | Rendered and parsed through Meridian's grammar | Rendered and parsed by `helix.naming` |
| `standards` | `{decision_table_version, logger, contract_format, layers_policy}` copied from the profile | Kept as a readable copy; `standards_bundle_digest` is the binding |
| Deployment keys | Appended to the client profile at merge | Declared in the bundle only; no profile write |
| `inputs.discover`, `inputs.estate_names`, `reuse[]`, `platform_objects` | Filled from Meridian's estate reads | Not read by B2. Their source needs a new design in LLD 05 and 06 before B3 and B4 |

## Not yet enforced in code

`helix validate` checks every field above when the naming contract is staged, which `helix verify` always requires. It does not yet check a flow per contract operation, or each key's `type` and `config_file`.

## Acceptance criteria

1. A bundle missing a required field, or with a malformed key entry, fails with `DESIGN_BUNDLE_INVALID`.
2. A bundle whose standards or naming digest differs from the staged input fails before generation starts.
3. A contract, HLD or LLD edited after gate two fails with `DESIGN_ARTEFACT_CHANGED`.
4. A production environment key in `environments[]` is refused.
5. The same bundle always produces the same digest and the same validation report.

## Required LLD reconciliation

- `06-b4-design.md` §3.13: add `standards_bundle_digest` and `naming_contract_digest`; take `environments[]` and every name from the naming contract; redesign the estate-derived fields.
- `07-b2-build-test-pr.md` §3.10.4: done on 2026-10-12.
- `08-b5-orchestration.md`: the gate-two record carries both digests.
