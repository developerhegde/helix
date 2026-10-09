# Changelog

## Unreleased — B1 client profile and offline doctor

- `helix.yaml` profile schema version 1, loader, and `helix doctor --profile DIR [--format text|json] [--strict]` with rules B1-001 to B1-015 and exit codes 0, 1, 2.
- Local policy table version 1, secret tripwire, structural adapter for the Meridian 1.8.1 profile files.
- Synthetic `acme-a` fixture; unit tests and guards for offline, read-only behaviour and rename-safe identifiers.
