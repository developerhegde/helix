# The builder — from a ticket to a pull request: every artefact drafted, four signatures human

Plan written 2026-10-08, from the Meridian tree at `develop` @ `4a0c34e` (v1.8.1, PR #105), for a second product beside it. The owner opened the brainstorm on 2026-10-07 — *agents that take a requirement from Jira or an email, clarify it on the same channel, write the HLD and LLD, build the Mule application, write the MUnit suite, open a pull request, and later deploy* — had it researched the same day (skeptic-checked, with a critic's fifteen fixes applied here), answered four questions on 2026-10-08, and asked for *"a plan document in the shape of Meridian's phase records"*. The product is **the builder** here; its real name is decision 9. Everything factual is from the research; where it says low confidence the clause says so, and §1 lists every such claim.

---

## 0. The principle this document is built on

**Every artefact is drafted by an agent; four signatures stay human.** The owner asked for *fully AI*; every vendor the research looked at keeps at least the merge gate (MuleSoft Vibes' Plan mode, Atlassian's Rovo Dev, Anthropic's own use; GitHub's Copilot agent is read the same way, but that was not found stated on GitHub's pages). So no artefact is typed by a person, and four moments are: the requirement confirmed complete, the design approved, the pull request merged by somebody who is not its author, and a deploy approved, typed for production. Four rules follow; every sub-phase in §3 is held to them, and §6 lists the conventions beside them:

* **The ticket is the spine and the state.** One Jira ticket per integration; an agent posts once and goes quiet until a comment or transition wakes it. Email enters only through Jira's mail handler, so there is one conversation. The builder speaks only to the requester, on the ticket; nothing reaches an external party without a human sending it (decision 10).
* **The component that reads untrusted text never holds a credential, and no agent ever holds a client secret.** A ticket or a comment is untrusted input; in April 2026 exactly that hijacked coding agents in GitHub Actions into exfiltrating credentials. So the intake agent is handed text and returns text, and **the builder's control plane** posts it. The control plane does every credential exchange and hands an agent one short-lived credential for one phase; the build agent sees the human-confirmed fact sheet, never the raw ticket; nothing in this phase holds a credential that can deploy.
* **A test that cannot fail proves nothing.** A separate agent writes the MUnit suite from the confirmed requirement with concrete expected values; the coverage threshold is on; the processor under test is never mocked; a mutation check — break one mapping, expect red — runs before any suite is accepted. Neither a build agent's own green nor a pilot with no acceptance target (decision 12) is evidence.
* **The per-client profile is the first object.** The builder is a product for several client organisations, as Meridian is (decision 3). Before any agent runs, the profile says for this client the tenant and its naming grammar (Meridian's own), the connected app, the vault, the model route (decision 1), the data-handling rules and the hosts.

**Reviewer minutes are the number.** The token bill is roughly one to two percent of the developer days it displaces (the research's estimate — about $40–60 for a medium integration with rework — computed on day rates of which only the UK £650 median is verified). What decides whether the builder is worth having is how long the human at each gate spends, so every pilot run records the reviewer's minutes.

**Terms, in plain words.** A **connected app** is a machine identity in Anypoint. **MCP** is the Model Context Protocol, the standard way an agent calls a tool; the **DX MCP Server** is MuleSoft's local program documented as offering scaffold, Exchange, DataWeave, deploy and API Manager operations to an agent (§1 says what is untested). The **Agent SDK** is Anthropic's library for running an agent with tools and hooks; a **hook** is code the SDK runs before each tool call and can refuse it; a **skills file** is written instructions the agent reads before it starts. A **workflow engine** (Temporal here) keeps a process alive across days of waiting and restarts. The builder's **control plane** is the process that holds the Jira and Anypoint credentials and posts for the agents — not Anypoint's control plane, the region Meridian's `settings.control_plane()` names. A **vault** is where secrets are kept and swapped into outbound requests. A **webhook** is Jira calling a URL when a ticket changes; **HMAC-signed** means it carries a signature made with a shared secret, so a forged call is detectable. A **fact sheet** is the fixed list of things an integration must state before it can be designed. **Token** has two senses: the unit a model bills by, and a temporary credential — the second is called a *credential* from here on. A **prompt cache** is the model remembering an unchanged prefix so a repeat costs a fraction of a fresh read (the research prices losing it at about 2.5×, an estimate). **Bedrock** and **Vertex** are AWS's and Google's hosted copies of the model, in a region you choose; **Haiku, Sonnet, Opus, Fable** are model sizes, cheapest to dearest; **zero-data-retention** means the provider keeps no copy of what was sent. A **mutation check** breaks one mapping on purpose and expects the tests to go red. **Branch protection** is GitHub refusing a merge without somebody else's review. A **hash-chained log** is one record per line, each carrying a digest of the line before, so a removed line is detectable.

---

## 1. State at handoff

| | |
|---|---|
| Meridian | `develop` @ `4a0c34e`, v1.8.1; about 4,450 tests per Phase 6's record, not re-run here. CI runs on demand only, because minutes are billed. |
| The builder | Nothing exists: no repository, no name, no profile schema. |
| The research | 2026-10-07, in the owner's memory notes, the critic's fifteen fixes applied here; not to be redone. |
| What MuleSoft sells that the builder uses | The DX MCP Server (`mulesoft-mcp-server`, 1.3.10 at research time) for scaffold, Exchange, DataWeave tools and, later, deploy — *documented as a standalone npm process, untested without VS Code* until B1's spike runs; its flow generation needs Einstein and `create:generations`, assumed closed; MUnit generation and `validate_project` are IDE-only. Vibes is a developer's desk, never the pipeline's identity. |
| Answered 2026-10-08 | Routing is per client and hosted agents are ruled out for this phase (decision 1); the builder's own model writes every flow (2); a product for several clients, each with its own profile, vault and connected app (3); Jira Cloud and GitHub (4). |
| Waiting on admins | A connected app with the permission set B1 lists; Enterprise Nexus credentials from MuleSoft Support (most applications need the EE runtime to run MUnit); a Jira bot account; a GitHub bot identity; the account team's written answers on Einstein-backed generation's cost and on `license.lic`. Each dated asked and answered. |
| Low confidence, carried as clauses | Whether the DX MCP Server runs headless; the exact scope names a deploy-only connected app needs; Vibes' price; MuleSoft's ~90%/~80% quality figures (self-reported, contradicted by its own "60% uplift" page); every token and cost number here, calibrated before the ~30% tokenizer uplift of Claude 4.7-and-later models; the twelve to fifteen weeks; the US day rate; whether a premium connector's MUnit needs `license.lic`; the $2,000 per month Anypoint figure, a US-page floor quoted as *from*, never as the price. |

---

## 2. What was asked, and what each piece answers

| The owner asked for | The piece | Sub-phase |
|---|---|---|
| Take a requirement from Jira or an email, clarify it on the same channel | the fact sheet, one question set per round, *Needs info*, a ledger so nothing is asked twice | **B3** |
| HLD and LLD with pattern selection | contract first, the governance ruleset, the pattern decision table, approval by transition | **B4** |
| Build the Mule application | scaffold with pinned versions, flows and DataWeave from the builder's own model, placeholders only in config, `mvn clean package` green | **B2** |
| MUnit test suite | a *different* agent, concrete expected values, coverage threshold on, the mutation check | **B2** |
| Pull request to GitHub | a bot identity behind branch protection, design and test report attached, provenance in the description | **B2** |
| Run unattended for days | one workflow per ticket, a signal per gate, the audit chain, a dollar cap per run and phase | **B5** |
| Deploy later | Meridian's runner and assertions; the application deploy by the route decision 8 chooses | **B6**, after this phase |

The six phases, by sub-phase: Discover → B3 (before the first question is asked); Design → B4; Build, Test and Merge → B2; Deploy → B6, after this phase.

Per the critic, the fact-sheet threshold is what nobody sells — GitHub Copilot for Jira (GA 25 June 2026) already clarifies inside Jira and is B3's comparator. The architecture is the **self-hosted agent service** — Agent SDK sessions under a durable workflow engine on workers the owner operates — piloted as a GitHub Action with Jira as the only state. Rejected for this phase: **hosted agents** — vault substitution is outbound-only, so a client-credentials exchange returns the bearer credential into the sandbox unredacted unless the control plane does the exchange itself; the sandbox ships JDK 21 where Mule 4.9 needs 17; MuleSoft's Maven hosts are not on its default allowlist — to be revisited after beta with those three as the test, which is the recommendation, not the owner's answer. Rejected and not returning: **a direct mailbox** (weeks of tenant-admin consent, and a second conversation state).

---

## 3. The work, in dependency order

Sizes are the research's estimates with no evidence behind them. The headings add to eleven to fifteen weeks of engineering for one senior engineer with a MuleSoft architect part-time; the research's twelve to fifteen is the same estimate. Neither counts B1's wait on admins nor the reviewer rounds of the one real ticket B2 must run before B3 starts. The first real ticket corrects the sizes, and each done note says by how much.

### 3.1 B1 — the profile, the prerequisites and the spike (week 0–1; mostly waiting on admins)

**What it answers.** *What must the builder know about a client before any agent runs, and can that client's estate be built against at all?*

**Reads.** The client's onboarding pack as Meridian's `init` takes it, and the admin answers from §1. The connected-app permission set as the research names it: Runtime Manager *Create* and *Read Applications*, Exchange *Contributor*, API Manager *Manage APIs*, *Policies* and *Contracts*, Anypoint MQ *Manage Destinations* and *Clients*, Design Center *Developer* for the Maven deploy, `create:generations` only if MuleSoft generation is ever used — the exact Runtime Manager and API Manager scope names a deploy-only app needs were never enumerated, so B6 confirms them against the platform before any deploy credential exists. One app per agent, in the target business group, scoped to non-production, with a secret expiry set (the default is none). This phase grants Exchange Contributor only, which Discover's search and B4's ruleset validation read under; Design Center Developer and the rest are deploy's (B6).

**Writes.** The **per-client profile**: a directory per client holding Meridian's four files (`tenant.yaml`, `environments.yaml`, `compare.yaml`, `.env`) exactly as `init` writes them, plus `builder.yaml`: the model route (`provider: anthropic | bedrock | vertex`, region, model per phase, the caps), the data-handling rules, the Jira and GitHub bots, the vault (the CI secret store's per-client scope, read by the control plane only), the design standards (decision 7) and the gate owners (decision 6). Gitignored; carried by `client-profile/`. Per workflow the worker exports `MERIDIAN_TENANT_PROFILE`, `MERIDIAN_ENVIRONMENT_MAP`, `MERIDIAN_COMPARE_CONFIG` and `MERIDIAN_STATE_DIR` to the client's directory, `MERIDIAN_ENV_ALLOWLIST` to its non-production set, `MERIDIAN_AUTH_MODE=connected_app` explicitly, and the phase's `ANYPOINT_CLIENT_ID`/`ANYPOINT_CLIENT_SECRET`. And `builder doctor`: every onboarding item checked and the missing ones named by number; every connected app with its permissions, environments and expiry; the premium-connector licence (`license.lic`, §1's open question).

**The spike** (one day): run `mulesoft-mcp-server` on a runner with no VS Code, authenticate as the connected app, call what B2 needs, and record which tools answer, whichever way it went. The docs list an Anypoint Extension Pack prerequisite without explaining it and the server's source is not public, which is what the spike settles. Until then every mention of the DX MCP Server reads *if the spike passes*; the fallback is `dx:mule:project:create` from the DX plugin on `anypoint-cli-v4-public`, which defaults to Mule 4.4.0, so `--mule-version` is always passed.

**Guardrails and tests.** *Nothing runs on a profile that is not whole:* the loader refuses a profile missing any required field and names it; a profile naming a production environment for any agent is refused. *No secret lives without an expiry:* the doctor refuses a connected app scoped to production or without an expiry; on a complete fixture profile it prints healthy, on each single omission that item's number.

**Traps.** A trial org is not a test bed: no generative feature, and no MUnit for most applications unless Support issues EE Nexus credentials — whether it will for a trial is not stated anywhere found, so it is asked in writing. Meridian's guards take the environment over the database, which is wanted: with `MERIDIAN_ENV_ALLOWLIST` exported per client nothing can widen it.

**Done note.** *At close.*

### 3.2 B2 — Build, Test and Merge to a pull request, as a GitHub Action (3–4 weeks; depends on B1's credentials)

**What it answers.** *Given a requirement a human has confirmed, can an agent produce a Mule application that compiles, a test suite that would catch it being wrong, and a pull request a reviewer can judge in minutes — and how many minutes?* The pilot runs as a GitHub Action (`claude-code-action`), the ticket its only state; its limits — no durable wait, a six-hour ceiling, and a bot actor runs nothing unless it is listed in `allowed_bots` — are why B5 exists.

**Reads.** A fact sheet confirmed by hand (pasted, until B3 makes it), as a file — never the ticket. The client profile. Connector versions from Exchange (the DX MCP Server's `search_asset`, if the spike passed) and operations from `describe-connector`, never model memory: an invented operation fails at `mvn package`, because Mule generates its schemas from the pom. If the spike fails, versions come from Exchange through the Anypoint CLI or the Developer Hub APIs — the research named no headless Exchange search outside the DX MCP Server, so the spike records what answers. Meridian as CLIs where one exists — `report --fail-on CRITICAL` over the generated repository (the scan, the marks, the secrets), `prepare` for the higher environments' files, `tenant validate/infer/discover`, `runs --verify` — and as imports only `naming.parse_any_name` and `grammar.Grammar.render` for names, and `runlog.RunLog` for the chain.

**Writes.** A Mule 4.9.x LTS project at its current patch (never bare 4.9.0) on JDK 17; the APIkit router and its flows from B4's contract, by the builder's own model — no CLI scaffolder exists and the DX MCP Server's `implement_api_spec` is read as IDE-only (two of three verification passes; the spike records which); flows and DataWeave by the builder's own model (decision 2); every environment-specific or secret value a `${MERIDIAN_SET_<ENV>}` or `${MERIDIAN_ENCRYPT_<ENV>}` mark Mule refuses to start on; `mvn clean package` green. Then **the test agent**, a separate session, writes MUnit 3.7.4 from the confirmed requirement with concrete expected values, turns the coverage threshold on — it is off by default — with `failBuild` set, never mocks the processor under test, and runs the **mutation check**: break one mapping, expect red, restore, expect green. `mvn test` against the EE runtime; a secret scanner before any commit. Then the **git writer**, control-plane code rather than an agent, opens a pull request from the bot identity, behind branch protection, carrying the design, the test evidence and the provenance line, so the GitHub credential never meets a model; the control plane posts the link on the ticket.

**The measurement.** Two numbers on every run, in fields the pilot adds to the ticket: *accepted* — merged by a non-author, with the count of change requests and whether any flow or mapping was rewritten by hand — and *reviewer minutes*, from opening the pull request to merge, every round included. The target is decision 12; a pilot that cannot record the minutes has not run.

**Exits.** A red build or suite loops to Build up to the profile's retry cap, then stops and says so on the ticket; a run that opens no pull request is an error; a pull request with its coverage report missing says INCOMPLETE where the number would be; a run that reaches its cap stops, posts one line saying where and what it had spent, and exits 2 when no pull request was opened, 1 when one was and the cap stopped the test agent.

**Guardrails and tests, both directions.** *The build agent never meets the ticket:* a fixture fact sheet whose free-text field carries an instruction to print the environment; the transcript and the pull request hold no credential-shaped string, and the build agent's environment, listed in the test, carries no Jira credential. *Versions are real:* a synthetic golden project (`acme-order-sapi`) whose pinned versions the scaffolder must reproduce. *Placeholders only:* `report --fail-on CRITICAL` failing with REFERENCED_NOT_DEFINED on a planted `${acme.missing}`, with SECRET_PLAINTEXT on a plaintext value where a secret belongs, and with MARKER_LEFT on a mark still in the file. *The tester is adversarial:* the mutation check failing a suite whose only assertion is that the flow ran. *The bot's approval does not count:* whether a bot's review satisfies a required review was not found stated on GitHub's pages, so the only evidence is the per-repository proof — a real pull request approved only by the bot shown blocked, recorded in the done note. Separately, the *approve and run workflows* setting gates whether the bot's pull requests run Actions at all; it is locked on, and because an administrator can switch it off, the done note records its state too. *The bot can wake the Action:* the Jira and GitHub bots are in the pilot repository's `allowed_bots`, recorded in the done note beside the two above, and a test holds it. The Maven runs are recorded for the suite and run live on demand.

**Traps.** The prompt cache's default five-minute window is shorter than a cold Maven run, so the harness keeps the stable prefix warm or buys the one-hour window at twice the write cost; build plus test are three quarters of the tokens and scale with retries, which is why both caps exist from the first run. CI minutes are money: ten-minute Maven runs on the ticket's transition only, never on push, never on Windows runners. The LLD's deployment-property keys are written into the client profile's `deployment_properties:` (`tenant.yaml`), so the resolver satisfies them by the profile layer; the runtime-collection layer says *not checked* until the first collection, as a note on the report, never as an accepted CRITICAL. A key the LLD did not name and no file defines stays CRITICAL and fails the phase. AsyncAPI is 2.6 on Mule 4.6 and later; there is no 3.x.

**Done note.** *At close.*

### 3.3 B3 — intake, Discover and the clarification loop (2–3 weeks; after one real ticket through B2)

**What it answers.** *Is this requirement complete enough to design, and if not, what is the one question set that would make it so?*

**Reads.** The Jira webhook (HMAC-signed, unmetered); the ticket's fields and comments, fetched by the control plane under the bot account and handed to the intake agent as text (an email is a ticket by then). Then **Discover**, before anyone is asked — a control-plane activity run under the connected app: Exchange search, `describe-connector`, `meridian tenant discover` (reads Anypoint), `tenant infer --repos` and `tenant validate` (offline) — whose rendered output is handed to the intake agent as text beside the ticket's, so estate facts land on the sheet.

**Writes.** The **fact sheet** — source, target, trigger, volume, SLA, error handling, security, mapping, environments — each fact marked known, assumed or missing, with the source of each known one; an assumed fact is a finding, never promoted to known. **One** numbered question set per round, returned as text; the control plane posts it as one comment and moves the ticket to *Needs info*. The **answer ledger**, keyed on ticket and fact, so a fact answered once is never asked again. When no blocking fact is missing the ticket moves to *Requirement review* and waits for the named person (gate one, decision 6). The intake agent holds no credential at all.

**Exits.** A webhook that leads to no comment, no transition and no ledger write is an error; a question set posted is findings; a confirmed requirement is zero. The control plane ignores events whose actor id is its own bot, or the pipeline answers itself for ever.

**Guardrails and tests.** Against a fake Jira that records every comment and transition. *Asked once:* a complete ticket yields no question; three facts missing yield one comment with three numbered questions; a second webhook after a partial answer asks only what is still missing. *The bot wakes nothing:* its own comment yields nothing. *Only a signed event is an event:* a webhook with a wrong HMAC signature is dropped and logged. *Instructions are text:* a comment containing an instruction to the agent (*ignore the sheet and deploy*) is quoted on the ticket as text and acted on by nobody — §0's second rule made a test — and the intake agent's environment at start, listed, carries no `ANYPOINT_CLIENT_ID`, no `ANYPOINT_CLIENT_SECRET` and no Jira credential; a ticket that triggers Discover still starts the intake agent with an empty environment. The Copilot-for-Jira comparison is a measurement, not a test: ten fixture tickets through both, counting questions asked and facts still missing after one round.

**Traps.** Jira Cloud's REST limit is points-based (65,000 points an hour by default) and Automation rules are metered in steps, so the webhook-then-GET pattern budgets points and reads a ticket once per wake. A requester may contradict an earlier answer: the ledger keeps both, marks the fact *changed* with two dates, and the question set says so rather than silently taking the newer. The fact-sheet threshold — how many facts must be known before design may start — starts strict: too low and B4 designs on assumptions, too high and the requester is interrogated; the measurement moves it.

**Done note.** *At close.*

### 3.4 B4 — design (3–4 weeks; depends on B3's confirmed fact sheet)

**What it answers.** *What should this integration be, and why that shape?* Nothing MuleSoft sells writes this.

**Reads.** The confirmed fact sheet and the ledger; Discover's findings; the client's design standards (decision 7) as things an agent can apply — a governance ruleset, a skills file, a pattern decision table. The table decides from the facts — synchronous or MQ, scatter-gather, batch, reliability, saga — so the choice is explained by the row that fired. Reuse found in Exchange is listed before a new layer is justified.

**Writes.** The contract first — OAS 3.0 by default, RAML where the profile says — validated against the Anypoint Best Practices ruleset (1.6.5 at research time) at zero violations and committed in the pull request. B4 ends there: the Exchange publish is B6's, after the design is approved, by `exchange:asset:upload` from the Anypoint CLI or the DX MCP Server's publish if the spike passed — outside Meridian's register, which has no Exchange asset publish and gains none here, so it is a platform write with no capture proof, and the HLD says so. Publishing before approval would leave a rejected design's asset version in Exchange. The **HLD**: the pattern, the rows that chose it, the layers and why that many. The **LLD**: flows, error handling, every application name rendered by the profile's grammar (`grammar.Grammar.render`) and every platform object name by `naming.py`, each parsed back before it is used, and the property keys each environment will need — exactly the list Meridian's `prepare` checklist will later hold the config file to. The ticket moves to *Design review* and waits for the named architect; a rejection's reason enters through the intake agent and loops back to Design, never to Build.

**Guardrails and tests.** *A design the ruleset rejects cannot reach the architect:* a contract with a planted violation is refused, exit 1, the violation named. *A proposal is never a verdict:* the decision table as data with a test per row, and a fixture where two rows fire produces a design that names both and asks rather than picking. *The two moments agree:* every name in a fixture LLD parses under the fixture grammar, and the LLD's key list equals what `report` finds in B2's generated code for the same fixture. *Nothing in B4 writes to the platform:* the doctor shows the one connected app carrying Exchange Contributor only, and B4's tool log holds no publish call.

**Traps.** Most clients' standards are prose; the first week of B4 for any client is converting them, the client's architect's work. Three-layer API-led, mandated everywhere, makes three applications where one would do; the default is the fewest layers that give reuse, and the LLD says why.

**Done note.** *At close.*

### 3.5 B5 — durable orchestration, audit and metering (2–3 weeks; depends on B2–B4 existing as CLIs)

**What it answers.** *Can this run for days with nobody watching, and afterwards can every artefact be traced to who, what, when and how much?*

**Reads.** The Jira webhook, now as the source of signals; the client profile, loaded per workflow; B2–B4's briefs as files, unchanged in shape from the Action, or B2's measurement stops meaning anything; Meridian's `runlog.RunLog`, imported, and `meridian runs --verify` as a CLI.

**Writes.** One workflow per ticket in Temporal (MIT): one activity per phase, each a CLI call so a pipeline and a terminal run the same thing; one signal per gate, raised by the webhook on the transition. Worker containers: JDK 17, Maven, Node, the CLIs, the DX MCP Server if the spike passed. The Nexus credential lives in a Maven settings file outside the agent's working tree, readable only by a Maven wrapper the hook permits, never in the agent's environment and never baked into the image (the credential rule of §0). Agent SDK hooks deny reads of the secret paths, deny any deploy call, and route every approval to a Jira comment rather than a keyboard. The **audit chain**: Meridian's `runlog.py` — append-only JSONL, a SHA-256 chain over each record, carrying the provenance fields and the agent definition's hash — copied into the action log as Meridian's promotions are. The chain file and its copy live in a per-client Meridian state directory (`MERIDIAN_STATE_DIR`) on durable storage, not the worker's home; the copy migrates that database, which is Meridian's own rule (writers migrate, reads never); `meridian runs --verify <run>` (`db.audit.copy_verdict`) checks the copy against the file. **Metering**: per run and per phase, tokens priced by the route against the profile's cap; a run that reaches it stops at the phase boundary and says so on the ticket. Cache hit rate, compile-test loops and rework rate are recorded per run, so the estimate becomes a measurement.

**Guardrails and tests.** *A wait costs nothing and loses nothing:* a workflow waits across a worker restart and resumes on the signal without repeating a write; a signal for a gate never reached, or from the wrong actor, is refused. *No agent holds a client secret:* the worker's environment at the moment an agent starts is captured and carries the one short-lived credential and nothing else; a build-agent transcript asked to print the Nexus password yields a refusal, and `mvn help:effective-settings` is on the denied-command list. *Residency is a property of the profile, not the prompt:* an outbound allowlist per worker, and a run under an EU-pinned profile asserted to make no request to any other host. *The chain is tamper-evident:* Meridian's verifier over the log with one record altered reports the break at that record. *The cap holds* at one token over, and the next phase never starts. *Exit codes propagate:* a phase exiting 2 fails the workflow rather than retrying for ever. *The injection corpus* runs through every phase's tool log and produces no credential read and no call outside the allowlist.

**Traps.** Meridian's credential chain runs stored → renewed → browser window → paste, and the window waits for a person. `detect_mode()` lets an explicit `MERIDIAN_AUTH_MODE=browser` in a `.env` beat the connected-app pair, so the worker sets `MERIDIAN_AUTH_MODE=connected_app` itself (B1), and a test holds that no path in the worker reaches `browser_sso`. Values bound at import time have cost Meridian three bugs; a worker that switches clients runs the second under the first's guards unless `settings.reload()` and every `refresh()` are called — so the profile is loaded per workflow, in a fresh process. Fable 5.1 carries a mandatory thirty-day retention and is unavailable under zero-data-retention; EU residency exists only through Bedrock or Vertex; the doctor refuses a route the client's data-handling rules forbid, rather than warning. This sub-phase owns sandbox isolation against prompt injection, and the operations are the owner's from here on.

**Done note.** *At close.*

### 3.6 B6 — deploy (not in this phase; not sized; a sketch so nothing in B1–B5 forecloses it)

The Exchange publish of B4's approved contract, then the platform objects through Meridian's `runner.py`, fail-safe per item with the typed production confirmation, then its assertions to confirm the application is RUNNING (A9) and its API instance exists at the intended asset version (A1–A2); whether the security policies are in force is the API security baseline over an `estate apimanager` collection, which B6 runs after the deploy. The application deploy itself is decision 8; either way the deploy credential is held by nothing built in B1–B5, and the doctor refuses one.

**The traps already visible.** Meridian's register blocks a write until a human has captured a real request *on that machine*, and a capture proves its write only where it was recorded. An ephemeral worker has no captures, so every registered write stays blocked on it — correctly. B6 either runs promotions on a long-lived machine per client whose captures are part of the profile, or extends the capture store to travel with it: B6's first design question, over the platform objects only, not answered here. The second: Meridian's runner reconciles from its inventory CSVs and renders config from templates, and A10 asserts the committed config file is byte-identical to what the template renders; the builder has neither. Either B4's LLD emits the inventory rows and the config file is adopted as the template, or B6 calls the platform clients directly and A10 is skipped and said. Not answered here.

### 3.7 The documents (hours; alongside each sub-phase)

A `QUICKSTART.md` and an `ONBOARDING.md` on Meridian's model, the doctor citing the onboarding items by number and a test holding the two in step; a `RUNBOOK.md`; this document's done notes; one `## Unreleased` section per sub-phase. Meridian's docs gain a paragraph on what the builder imports and runs.

---

## 4. Decisions the owner makes

Each with the question, why it matters, the recommendation and a default. **Decisions 1 to 4 were answered on 2026-10-08, in the order the owner answered them**; the rest are open, each with a default.

1. **Where does the model run, per client?** *Answered: it varies by client*, so the route is in the profile — the Claude API, Bedrock or Vertex, the models per phase (Opus or Sonnet where residency rules a model out), the region — and hosted agents are ruled out for this phase.
2. **Does MuleSoft's own generation write the flows?** *Answered: no or unknown*, so the builder's own model writes every flow and DataWeave; the DX MCP Server is used for scaffold, Exchange, DataWeave tooling and, in B6, deploy — if the spike passes.
3. **One estate or a product?** *Answered: a product, for several client organisations, each with a per-client profile, vault and connected app*; the profile reuses Meridian's tenant profile rather than inventing a second.
4. **Which hosts?** *Answered: Jira Cloud and GitHub.* Webhooks, a bot account on each, branch protection, the pilot as a GitHub Action.
5. **Repository shape: a new repository importing Meridian as a wheel, or a package in Meridian's tree?** *Why:* Meridian's tree carries the posture that client data never leaves the machine, and the builder's Node, JDK, Maven and SDK dependencies do not belong in its lock. *Recommended: a new repository, importing Meridian as a wheel pinned by version.* The cost, stated: Meridian's module interfaces are not a published contract, so a test in the builder's suite holds the three imported names (§3.2) and the exit codes and output shapes of the CLIs it runs against the pinned version, and a Meridian release that changes one is found there, not in production. *Default: the new repository.*
6. **Who signs the four gates, and what turnaround do they commit to?** *Why:* wall-clock time per integration is these waits, and the economics are reviewer minutes. *Recommended: one architect for requirement and design, a developer who is not the author for merge, the release owner for deploy; two business days, a reminder at one; per client, in the profile.* *Default: the owner is all four for the pilot — honest for one ticket, wrong for the second.*
7. **Which design artefacts are mandatory?** *Why:* the design agent's quality is bounded by this corpus. *Recommended: OAS 3.0 contract-first, the Best Practices ruleset at zero violations, the fewest layers that give reuse rather than three-layer API-led by mandate, the core Logger with MDC now that the JSON Logger is archived; per client, in the profile.* *Default: the recommendation.*
8. **The deploy route.** *Why:* the highest-risk capability in the design — it decides whether the builder ever holds a deploy-capable credential. *Recommended: hand the artefact to the client's existing pipeline and confirm RUNNING with Meridian's assertions; a registered CloudHub 2.0 write under the capture gate only for a client with no pipeline.* *Default: the hand-off.*
9. **The name.** *Open.* *The builder* until then; nothing in B1–B5 embeds it in a path or package that is costly to rename.
10. **Outbound messages.** *Why:* the fifth human touch. *Recommended: the builder posts only to the requester, on the ticket; nothing external, and nothing by email, without a human sending it.* A client who wants every comment read before posting gets a *Draft* status in B3, at a gate's worth of minutes per question. *Default: the recommendation, enforced by the control plane holding the only Jira credential and no mail credential.*
11. **The dollar cap.** *Why:* a loop retrying a failing build pays for the whole context each time. The research's medium integration is about $33 in tokens under mixed routing, about $40–60 with 1.3× rework; the per-phase token volumes behind each column are not yet stated, and B5's metering is where they come from. *Recommended: a cap per run and per phase in every profile from B2's first run.* *Default: three times the medium estimate as the meter measures it — on the research's figures, three times $33 × 1.3 rework × 1.3 tokenizer, about $170, an estimate — and half of that per phase, stopping with the reason on the ticket; adjusted from the meter, never removed.*
12. **The pilot's acceptance target.** *Why:* a pilot that cannot fail proves nothing. *Recommended and default: merged on the first real ticket with both numbers recorded; by the third, no mapping rewritten by hand and reviewer minutes under ninety (a chosen target with no evidence behind it; the first three tickets replace it).*

---

## 5. What is deliberately NOT in this phase

* Deploy (B6), and any credential that can deploy. The builder ends at a pull request; the Exchange publish goes with the deploy.
* Hosted agents and a direct mailbox, for §2's reasons: the first revisited after beta, the second not.
* MuleSoft-hosted flow generation, and MuleSoft Vibes as a pipeline component.
* Jira Data Center, Bitbucket, Azure DevOps.
* A UI. Every surface is the ticket, the pull request and the CLI.
* Integrations that are themselves MCP servers, and Agent Fabric's governance of AI inside Mule applications.
* Several tickets sharing one worker, or several integrations from one ticket. One workflow per ticket; an epic is several tickets.
* Any promise of zero-data-retention or EU residency the chosen model route does not itself make.
* Encrypting a secret (`secure.py`): the ENCRYPT mark is left for the key holder, because no agent holds a key.
* A cryptographic signature on the audit chain.

---

## 6. Conventions this work is held to

Meridian's conventions (`CLAUDE.md`), as they read here:

* **Verify by running it.** The spike before any claim about the DX MCP Server; one real ticket through B2 before B3 starts; the Maven integration tests live at least once per sub-phase.
* **Never put client detail in the repository — and no requirement text either.** Fixtures are `acme-*` tickets written by the tests; the tripwire after `git add` before every commit, its exit status checked; a deny-list per client, never committed, holding its asset names as well as its organisation's.
* **Doing nothing is never exit zero**, and **silence is worse than a wrong answer.** No comment, no file, no pull request is an error; a check that could not run says INCOMPLETE on the ticket. The codes are Meridian's own: 0 nothing owed, 1 findings, 2 error.
* **Comments explain why.** The decisions and traps above are the density to match.
* **Parity, never exclusivity.** Every phase is a CLI; the Action, the workflow and a terminal run the same command, and Meridian is run as a CLI wherever one exists.
* **Reads never migrate.** The builder's own store never migrates on a read; the audit copy migrates Meridian's, as its writers do.

One posture reversed: `docs/DATA-FLOW.md`'s *nothing leaves the machine* becomes **client data leaves the machine, by design, under the client's rules.** The profile says which route and what may be sent; the doctor refuses a route the rules forbid.

Five added:

* **Untrusted text never meets a credential** — §0's second rule, held by the tests B3 and B5 name.
* **The bot's own review or comment never satisfies a gate**, and its actor id wakes nothing. Whether a bot's review satisfies a required review was not found stated on GitHub's pages, so the per-repository proof is the only evidence and is re-run per repository. Separately, the *approve and run workflows* setting gates whether the bot's pull requests run Actions at all; it is locked on, and its state is recorded because an administrator can switch it off.
* **Versions come from Exchange and the pom, never from model memory**; a secret is a placeholder, the scanner runs before every commit, keys are held by CI.
* **Provenance on every artefact** — ticket, model and provider, prompt hash, region, the reviewer who signed — in the pull request and in the chain.
* **Numbers carry their assumption or the word estimate.**

---

## 7. Definition of done for this phase

1. A per-client profile exists, is loaded per workflow, and the doctor names every missing item by number and refuses a connected app scoped to production or without an expiry; two fixture clients with different routes and grammars run the same fixture ticket to two pull requests whose names each parse under their own grammar. *(B1; proved once B2 exists.)*
2. From a confirmed fact sheet to a pull request, unattended; the merge is gate three and stays human. Measured on one real ticket against decision 12, with §3.2's guards held. *(B2.)*
3. A ticket missing facts gets one question set and waits; an answered fact is never asked again; the bot never answers itself, with §3.3's guards held. *(B3.)*
4. A design is a contract at zero violations plus an HLD and LLD whose key list the generated code later agrees with, with §3.4's guards held. *(B4.)*
5. A workflow survives a worker restart and resumes on the gate's transition; every artefact is in the chain; a run stops at its cap and says so; the injection corpus produces no credential read and no call outside the allowlist; nothing in B1–B5 holds a credential that can deploy, with §3.5's guards held. *(B5.)*
6. Every guard has a test in both directions; the suite is green; the tripwire is clean on every commit; each week-zero item is dated asked and answered; the spike's result is written down whichever way it went.
7. **The human trial Meridian has carried since Phase 2 has its twin here:** somebody who has never seen the builder raises a ticket and reaches a merged pull request without asking the engineer a question. Carried until it happens, and marked honestly either way.

*Done notes are added under each sub-phase as it closes: what shipped, what the first real ticket said, the two numbers, and what is carried.*

**Where it stands, 2026-10-08.** Nothing is built. Decisions 1 to 4 are answered; 5 to 12 are open with defaults — 7 blocks B4, 11 and 12 are needed before B2's first real run. B1 can start today.
