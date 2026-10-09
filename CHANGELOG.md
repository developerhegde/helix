# Changelog

## Unreleased — B1 client profile and offline doctor

- `helix.yaml` profile schema version 1, loader, and `helix doctor --profile DIR [--format text|json] [--strict]` with rules B1-001 to B1-014 and exit codes 0, 1, 2.
- Local policy table version 1 and secret tripwire. Helix is standalone: no Meridian dependency, files or rule.
- Synthetic `acme-a` fixture; unit tests and guards for offline, read-only behaviour and rename-safe identifiers.
