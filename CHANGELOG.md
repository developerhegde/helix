# Changelog

## Unreleased — B2 standalone validation foundation

- `helix validate`, the `naming_contract.v1` compiler, the client standards bundle loader, and doctor rules B1-015 (naming) and B1-016 (standards bundle).
- Isolated Maven runner and MUnit/coverage report parser producing value-free evidence.
- Naming checks NAM-001 to NAM-007 in `helix validate`, path-aware mark and plaintext-secret checks, the `incomplete` verdict, and `helix verify` (Maven, fresh evidence, then validation).
- `deployment_properties` configuration layout in the naming contract and the validator, beside `environment_files`; new finding `KEY_ENVIRONMENTS_UNEVEN`.
- Doctor rules B1-017 (`client_id` equals the profile directory name) and B1-018 (unknown top-level key, a warning); findings sorted by rule id.
- Doctor: `vault://` references must sit inside `vault.scope` (B1-009); the profile must agree with the standards bundle (B1-019); platform names follow `anypoint.environments` (B1-020); bundle-listed files are digest-checked (B1-016).
- Design: profile schema reconciliation, deciding thirteen differences between the B1 contract and LLD 02.
- Design: B2 contracts for validation, naming, Maven/MUnit execution, the standards bundle and the design bundle; LLD 07 revised to the standalone design; marks renamed to `HELIX_SET_` and `HELIX_ENCRYPT_`; default coverage minimum 75.

## Unreleased — B1 client profile and offline doctor

- `helix.yaml` profile schema version 1, loader, and `helix doctor --profile DIR [--format text|json] [--strict]` with rules B1-001 to B1-014 and exit codes 0, 1, 2.
- Local policy table version 1 and secret tripwire. Helix is standalone: no Meridian dependency, files or rule.
- Synthetic `acme-a` fixture; unit tests and guards for offline, read-only behaviour and rename-safe identifiers.
