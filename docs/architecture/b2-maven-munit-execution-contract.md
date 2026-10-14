# B2 architecture decision — isolated Maven/MUnit execution contract

## Decision

Helix runs Maven and MUnit only through a dedicated verifier process. The verifier receives an explicit project directory and an explicit Maven settings file, constructs a minimal environment, and writes a value-free execution receipt. It never receives a client credential, a profile directory, shell input, or inherited environment variables beyond `HOME`, `LANG`, `PATH`, and `TMPDIR`.

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

## Live run: what it needs

The sample application `tests/fixtures/acmeb-sapi-order-v1/` passes every static check Helix has, with synthetic evidence. It has never been built by Maven. A live run needs, on the machine that runs it:

1. JDK 17 and Maven 3.9.
2. A Maven `settings.xml` holding the owner's access to MuleSoft's enterprise repository. Helix never reads or writes that credential; `helix verify` only passes the file's path to Maven.
3. The client's parent POM (`acme-b-org-id:acme-b-mule-parent:1.0.0` for the fixture) installed in the local repository. No parent POM is checked in yet; it is to be written against a real build, because its plugin versions and report settings are the external facts listed above.

Then:

```text
helix stage  --profile <acme-b profile> --out-dir <staged>
helix verify --project <application> --bundle <design bundle> --policy <staged>/validation-policy.json \
             --naming-contract <staged>/naming-contract.json --settings <settings.xml>
```

## Acceptance criteria

1. The runner refuses relative project, settings, or output paths and command-option injection through goals.
2. The runner emits canonical, value-free receipts for success and non-zero Maven exit codes.
3. The runner passes only its minimal environment to Maven.
4. A parser can transform only approved report files into `mule_validation_evidence.v1`.
5. `helix validate` rejects missing, malformed, failed, or below-threshold evidence.
