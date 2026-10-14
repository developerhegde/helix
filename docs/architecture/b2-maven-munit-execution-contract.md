# B2 architecture decision — isolated Maven/MUnit execution contract

## Decision

Helix runs Maven and MUnit only through a dedicated verifier process. The verifier receives an explicit project directory and an explicit Maven settings file, constructs a minimal environment, and writes a value-free execution receipt. It never receives a client credential, a profile directory, shell input, or inherited environment variables beyond `HOME`, `JAVA_HOME`, `LANG`, `PATH`, and `TMPDIR`. `JAVA_HOME` selects the JDK 17 that Mule 4.9 needs.

The first executable interface is:

```text
helix.validation.maven_runner.run(
  project_dir: absolute directory,
  settings_path: absolute file,
  output_path: absolute file,
  maven_path: "mvn",
  goals: ("clean", "test"),
) -> mule_execution_receipt.v1
```

The runner invokes:

```text
mvn --batch-mode --no-transfer-progress --settings <settings> clean test
```

A wrapper or container runtime supplies the Maven repository location and proxy-only networking. The runner itself has no network policy logic and does not parse project output.

## Receipt contract

The runner writes canonical JSON to the requested output path:

```json
{
  "schema": "mule_execution_receipt.v1",
  "command": ["mvn", "--batch-mode", "--no-transfer-progress", "--settings", "<settings>", "clean", "test"],
  "exit_code": 0,
  "duration_ms": 1234,
  "stdout_sha256": "<sha256>",
  "stderr_sha256": "<sha256>"
}
```

The receipt intentionally contains no output text, test names, property values, secret material, or credential paths. It proves only the command shape, outcome, duration, and immutable output digests.

## Evidence boundary

`mule_execution_receipt.v1` is not `mule_validation_evidence.v1`.

A separate report parser converts allowlisted MUnit/Surefire and coverage report files into the existing value-free evidence summary:

```json
{
  "schema": "mule_validation_evidence.v1",
  "maven": {"exit_code": 0},
  "munit": {"tests_run": 4, "failures": 0, "errors": 0},
  "coverage": {"application_percent": 80.0}
}
```

`helix validate` consumes this summary, validates the project against its staged contracts, and never parses unbounded Maven logs.

## Report-parser contract

The parser accepts only explicit, project-relative paths beneath the generated tree:

```text
helix.validation.report_parser.parse(
  project_dir,
  receipt_path="target/maven-execution.json",
  munit_report="target/munit-results.xml",
  coverage_report="target/coverage-summary.json",
  output_path="target/helix-validation-evidence.json",
) -> mule_validation_evidence.v1
```

- The execution receipt must be `mule_execution_receipt.v1`.
- The MUnit report is JUnit XML: a root `testsuite` or `testsuites` containing `testsuite` elements, each with non-negative `tests`, `failures`, and `errors` counts.
- The coverage summary is a JSON object with `application_percent` between 0 and 100.
- The parser aggregates only numeric counts and coverage. It never copies suite names, failure text, payloads, logs, property values, or filesystem paths into evidence.
- Missing or malformed receipt/report files stop evidence generation; `helix validate` then reports `MAVEN_EVIDENCE_MISSING` or `MAVEN_EVIDENCE_INVALID`.

The checked-in `acme-order-sapi` fixture includes synthetic execution, MUnit, and coverage reports. They prove the parser and validation boundary without requiring Maven or a client dependency repository.

## Remaining external facts

Before enabling a real Maven/MUnit run, confirm against the approved parent POM:

- exact MUnit/Surefire result-file locations and schemas;
- exact coverage report location and application percentage field;
- Maven wrapper/container repository location and proxy-only settings layout;
- test-selection and coverage properties supplied by the parent POM.

## Live run results (2026-10-14, macOS, no enterprise repository access)

The sample application `tests/fixtures/acmeb-sapi-order-v1/` and its client parent POM `tests/fixtures/acme-b-mule-parent/` were built with real Maven against MuleSoft's public repository only.

| Step | Result | What it settles |
| --- | --- | --- |
| Install the parent POM | Success | The parent pins every version; the child pins none |
| `mvn package -DskipMunitTests` | **Success**: a 68 MB `mule-application` archive | Every build piece the sample uses is public: Mule Maven plugin 4.10.2, MUnit 3.7.4, HTTP connector 1.12.2, APIkit 1.13.0, secure properties module 1.3.1. Packaging needs no enterprise access |
| `mvn test` (MUnit) | Fails: `mule-runtime-impl-no-services-bom:4.9.1` not found | MUnit's enterprise runtime is the one piece that needs MuleSoft's enterprise repository |

Toolchain facts found on the way:

- **Maven 3.9, not 3.10.** Mule Maven plugin 4.10.2 fails on Maven 3.10.0 with `NoSuchMethodError` in the resolver (`DefaultMirrorSelector.add`). Maven 3.9.16 works, matching conventions §2. Homebrew installs 3.10; take 3.9 from Apache's archive.
- **JDK 17 through `JAVA_HOME`.** Maven otherwise runs on the newest installed JDK. The runner passes `JAVA_HOME` through.
- **The plugin reads MuleSoft's runtime support matrix from GitHub** (`raw.githubusercontent.com`) when packaging, and plugin 4.10.2 has no usable bundled copy. A machine that cannot reach GitHub cannot package. On the build machine the JVM timed out over IPv6 and needed `-Djava.net.preferIPv4Stack=true` in `MAVEN_OPTS`; that is a machine setting, not a project one.

Still open: the MUnit report and coverage file locations (the external facts above) need one passing MUnit run, which needs enterprise access.

## Live run: what it needs

The next live run, with MUnit, needs on the machine that runs it:

1. JDK 17 and Maven 3.9.
2. A Maven `settings.xml` holding the owner's access to MuleSoft's enterprise repository. Helix never reads or writes that credential; `helix verify` only passes the file's path to Maven.
3. The client's parent POM installed in the local repository (`tests/fixtures/acme-b-mule-parent/` for the fixture).

Then:

```text
helix stage  --profile <acme-b profile> --out-dir <staged>
helix verify --project <application> --bundle <design bundle> --policy <staged>/validation-policy.json \
             --naming-contract <staged>/naming-contract.json --settings <settings.xml> --maven <maven 3.9>/bin/mvn
```

## Acceptance criteria

1. The runner refuses relative project, settings, or output paths and command-option injection through goals.
2. The runner emits canonical, value-free receipts for success and non-zero Maven exit codes.
3. The runner passes only its minimal environment to Maven.
4. A parser can transform only approved report files into `mule_validation_evidence.v1`.
5. `helix validate` rejects missing, malformed, failed, or below-threshold evidence.
