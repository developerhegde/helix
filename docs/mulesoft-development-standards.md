# MuleSoft Development Standards

**Version:** 1.1  
**Date:** 2026-10-09  
**Status:** Sanitized, version-control-friendly source  
**Canonical source:** This Markdown file; `MuleSoft Development Standards.docx` is the original export.

## Purpose and scope

Every Mule 4 application the integration team ships must meet every **Blocking** rule before its pull request merges. **Advisory** rules are expected; an advisory waiver needs a written reason in the pull request.

These standards apply to Experience, Process, and System APIs, batch jobs, event-driven integrations, shared libraries, and API fragments published to Exchange. Rules marked **(org)** are organization choices; all others reflect MuleSoft documentation or ordinary engineering practice.

Client-specific values must be supplied through Helix's approved standards bundle, never inferred from a ticket or model memory.

## Rule strength

- **Must / Blocking:** CI or a reviewer rejects the pull request.
- **Should / Advisory:** reviewer finding; may be waived in the pull request.
- **May:** team choice.

## Naming

| Object | Standard |
| --- | --- |
| Git repository / Maven `artifactId` | `<domain>-<layer>-v<major>`; layer is `exp`, `prc`, or `sys` **(org)** |
| Exchange API specification | `<domain>-<layer>-api`; title spells the layer out **(org)** |
| Runtime application | `<artifactId>-<env>`; the environment suffix is deployment-only **(org)** |
| API base path | `/api/v<major>/<resource>` **(org)** |
| Global configuration | `global.xml`, `<name>-api.xml`, `<resource>-impl.xml`, `error-handler.xml` |
| APIkit flow | Keep the generated name verbatim |
| Implementation flow | `<verb>-<resource>-flow` **(org)** |
| Sub-flow | `<action>-<object>-subflow` **(org)** |
| Connector configuration | `<system>-<connector>-config`; listener is `http-listener-config` **(org)** |
| Property key | lowercase dot path, such as `erp.http.host`; secrets use `${secure::<key>}` |
| Flow variable | camelCase |
| DataWeave script | `src/main/resources/dwl/<resource>/<purpose>.dwl`, kebab-case |
| DataWeave module | `src/main/resources/modules/<Module>.dwl`, imported as `modules::<Module>` |
| Custom error type | `APP:<UPPER_SNAKE_REASON>` |
| MQ destination | `<domain>-<event>-<env>`; DLQ is `dlq-<queue>` |
| Object Store | `<purpose>-os` |
| API Manager client application | `<consumer>-<env>` |
| Git branch | `feature/<ticket>-<slug>`, `bugfix/<ticket>-<slug>`, `hotfix/<ticket>-<slug>`, or `release/<semver>` |
| Commit message | `<TICKET>: imperative summary`, maximum 72 characters |

### Naming rules

- Kebab-case is required except for DataWeave modules (PascalCase), flow variables (camelCase), and error reasons (UPPER_SNAKE). **Blocking**
- Environment tokens never occur in a repository name, Exchange asset name, or Maven `artifactId`; append them only at deployment. **Blocking**
- A new API major version requires a new repository and artifactId. **Blocking**
- APIkit flow names are never changed. **Blocking**
- Every processor should carry an intent-based `doc:name`. **Advisory**

## POM, runtime, and dependencies

- Every application inherits the approved parent POM. The child POM contains only application-specific coordinates, dependencies without versions, and approved application properties. **Blocking**
- Use Mule 4.9 LTS and Java 17. Edge releases do not reach UAT or production. **Blocking**
- `mule-maven-plugin`, `munit-maven-plugin`, connector versions, shared-library versions, and coverage configuration are pinned in the parent POM. **Blocking**
- Maven coordinates use the Anypoint organization or business-group ID. `artifactId` follows naming rules and semantic versioning. **Blocking**
- No version ranges, `LATEST`, or `RELEASE`. **Blocking**
- Use MuleSoft-supported Exchange connectors and approved shared libraries only. Community/custom connectors require architecture approval and a recorded security scan. **Blocking**
- The API specification is consumed from Exchange as a dependency; it is not copied into `src/main/resources/api`. **Blocking**
- JDBC drivers and comparable JARs are configured through `sharedLibraries` and parent dependency management. **Blocking**
- Test-only dependencies have test scope. Run `mvn dependency:analyze`; remove unused declared dependencies. **Advisory**
- `mule-artifact.json` declares the approved minimum Mule version, Java 17, and every secure property key. **Blocking**

## Build and deployment configuration

- Deploy shared environments through CI/CD and the Mule Maven plugin. Manual Runtime Manager uploads must be redeployed through the pipeline before promotion. **Blocking**
- Pipeline variables parameterize environment, application name, and sizing. Do not use per-environment Maven profiles. **Blocking**
- Anypoint and Exchange credentials live only in the CI secret store or settings file; never in POM files. **Blocking**
- Do not override `finalName`. **Blocking**
- Run tests before packaging. Packaging may skip tests only after the test stage passed. **Advisory**

## APIkit and API design

- Design and publish RAML 1.0 or OAS 3.0 specifications before implementation. **Blocking**
- The specification passes the Anypoint Best Practices governance ruleset at zero violations. **Blocking**
- Reuse organization Exchange fragments for common traits, types, errors, and client-id enforcement. Do not redefine local copies. **Blocking**
- Use plural resource nouns, path parameters for identifiers, query parameters for filtering/paging, camelCase JSON fields, ISO-8601 UTC timestamps, explicit currency codes, and documented success plus 400/401/403/404/500 responses. **Blocking**
- Configure one APIkit router per application using the Exchange dependency. Generated flows only delegate to implementation flows; request validation remains enabled. **Blocking**
- Configure API console state, listener base path, correlation ID behavior, API autodiscovery, and APIKIT error mapping through properties and the global configuration. **Blocking**

## Configuration and secrets

### Layout

```text
src/main/resources/
  config.yaml
  config-secure.yaml
  tls/
<pipeline repository>/
  <app>/dev.yaml
  <app>/test.yaml
  <app>/uat.yaml
  <app>/prod.yaml
```

- `config.yaml` provides a default for every application property.
- Environment overrides are deployment properties supplied only by the pipeline. Each environment has the same property-key set. **Blocking**
- Use `config-secure.yaml` and `${secure::<key>}` for encrypted secrets. **Blocking**
- Every host, port, path, credential, timeout, pool size, cron expression, queue, and feature flag is a property; do not hard-code these in Mule XML or DataWeave. **Blocking**
- Feature flags are `feature.<name>.enabled` and default to `false`. **Advisory**
- API Manager resources and queues are created through the pipeline; `api.id` is captured rather than hand-entered. **Advisory**

### Secure key clarification

The **real** `secure.key` never appears in a repository file, POM, log, README, or test resource. It is a protected deployment property supplied by the platform/pipeline secret store.

A synthetic, non-secret dummy value may be supplied only to the parent-POM test configuration so MUnit can load sanitized fixture secure properties. It must not be named, reused, or accepted as a deployment credential.

### Secret rules

- Encrypt every password, client secret, API key, token, keystore password, and private key with Secure Configuration Properties; reference it only as `${secure::<key>}`. **Blocking**
- Any plaintext secret in files, comments, test resources, or history is a Blocking finding and is rotated the same day. **Blocking**
- Use one encryption key per environment, held only in the organization secret store. **Blocking**
- `secureProperties` lists every secure property name and `secure.key`, so Runtime Manager masks them. **Blocking**
- Private keys for UAT/production are never committed. Truststores containing public certificates may be committed. **Blocking**
- Local defaults and test overrides contain synthetic credentials only. **Blocking**
- Ignore `settings.xml`, `.env`, `*.key`, and local override files. **Blocking**

## Logging and error handling

### Logging

- Use JSON logging through the organization's JSON Logger Exchange module or one approved `log-event` sub-flow; free-text `<logger>` components are a review finding. **Blocking**
- Each log event includes UTC timestamp, level, appName, environment, correlationId, flowName, and message. Outbound calls include system, operation, elapsedMs, and status; errors include errorType and errorDescription. **Blocking**
- Log request receipt, each outbound call, request completion, and handled errors. **Blocking**
- Production root level is INFO. DEBUG is only for dev/test and is property-controlled. TRACE is prohibited. **Blocking**
- Never log secrets, authorization headers, personal data, or unmasked payloads. Payload logging is DEBUG-only and disabled in UAT/production. **Blocking**
- Preserve Mule correlationId: adopt inbound `x-correlation-id`, forward it downstream, and do not replace it with a custom variable. **Blocking**

### Error handling

- Register one global error handler in `error-handler.xml`; flows do not define their own handlers except a scoped, documented recovery. **Blocking**
- Default to `on-error-propagate`. A continue path requires a specific fallback, named error types, WARN-or-higher logging, and a rationale. **Blocking**
- Raise business errors as `APP:<REASON>`. Translate connector errors at the integration boundary. **Blocking**
- Retry only idempotent operations; retry settings come from properties. **Blocking**
- Event-driven failures propagate to nack or dead-letter handling. **Blocking**
- Every error branch sets HTTP status and renders the shared error envelope. **Blocking**

### Error envelope

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Order 12345 was not found",
    "correlationId": "6f1c2a8e-…",
    "timestamp": "2026-10-09T15:10:00Z",
    "details": [{"field": "lineItems[0].quantity", "issue": "must be greater than 0"}]
  }
}
```

`APP:ORDER_NOT_FOUND` is the internal Mule error type. The consumer-facing envelope code is `NOT_FOUND`, matching the mapping table.

| Error type | HTTP | Consumer code |
| --- | --- | --- |
| `APIKIT:BAD_REQUEST`, `APP:VALIDATION` | 400 | `VALIDATION_FAILED` |
| `APIKIT:NOT_FOUND`, `APP:*_NOT_FOUND` | 404 | `NOT_FOUND` |
| `APIKIT:METHOD_NOT_ALLOWED` | 405 | `METHOD_NOT_ALLOWED` |
| `APIKIT:NOT_ACCEPTABLE` | 406 | `NOT_ACCEPTABLE` |
| `APP:CONFLICT` | 409 | `CONFLICT` |
| `APIKIT:UNSUPPORTED_MEDIA_TYPE` | 415 | `UNSUPPORTED_MEDIA_TYPE` |
| `APP:BUSINESS_RULE` | 422 | `BUSINESS_RULE_VIOLATION` |
| Downstream 4xx/5xx | 502 | `UPSTREAM_ERROR` |
| Connectivity/service unavailable | 503 | `UPSTREAM_UNAVAILABLE` |
| Timeout | 504 | `UPSTREAM_TIMEOUT` |
| Catch-all | 500 | `INTERNAL_ERROR` |

## Connectors

- Use approved connectors only, configured once in `global.xml`. **Blocking**
- Connector configurations include property-driven host, port, path, credentials, timeout, and reconnection strategy. **Blocking**
- HTTP requests have explicit timeouts and preserve standard response validation. **Blocking**
- Database access uses parameterized queries, explicit columns, pooling, and timeout properties. **Blocking**
- MQ consumers use manual acknowledgement, DLQ, redelivery limits, message-id idempotency, and correlation ID propagation. **Blocking**
- File/SFTP, Salesforce, Object Store, Scheduler, and Web Service Consumer follow their documented property, timeout, idempotency, and security requirements. **Blocking**

## MUnit and coverage

- One suite per implementation file in `src/test/munit/`; tests use behavior, execution, and validation sections. **Blocking**
- Every external system is mocked by `doc:name`; the flow under test, DataWeave transforms, and APIkit router are never mocked. **Blocking**
- Test external DataWeave scripts, business validation, raise-error paths, global error handling, API operations, and event acknowledgements/dead-letter behavior. **Blocking**
- Tests are independent, do not sleep, clear test state, and do not ignore tests without a ticket reference. **Blocking**
- Test resources contain synthetic data only. **Blocking**
- Parent POM enforces `failBuild=true` and minimum coverage: application 75%, resource 50%, flow 50%. **Blocking**
- New exclusions require justification and reviewer approval. Generated APIkit flows are not excluded. **Blocking**
- Publish console/HTML/JSON/Sonar coverage reports as artifacts. **Advisory**

## Pull-request review

- Protected `main` and `release/*` branches require an approval by a non-author; a `hotfix/*` change heading to production requires **two** non-author approvals. **Blocking**
- CI build, MUnit, coverage, secret scan, and static checks pass before review begins. **Blocking**
- Every Blocking finding is fixed. Advisory findings are fixed or answered in the thread. **Blocking**
- A reviewer cannot downgrade a Blocking finding; architecture exceptions are recorded in the pull request. **Blocking**
- Merge to main bumps the version and updates the changelog. **Blocking**
- First review response within one business day and PRs of roughly 400 changed lines are recommended. **Advisory**

## Helix mapping

Helix's client standards bundle must encode the deterministic Blocking rules above: naming grammar, runtime/POM baseline, API contract policy, configuration/secret policy, JSON Logger requirement, error-envelope mappings, approved connectors, MUnit rules, coverage thresholds, and review policy. Guidance that needs human judgment remains a reviewer checklist.
