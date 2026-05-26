# Software Engineer Team — Agentic Architecture

> **Role of this document:** Authoritative design for the CrewAI multi-agent
> software engineering team. It defines the agents, the task graph, the
> context-passing contract, the synchronization model, and the extension points.
> Implementation lives elsewhere; this is the blueprint.

---

## 1. Design Principles

1. **One source of truth.** The Architect emits a single structured `SystemDesign`
   artifact (Pydantic) that every downstream agent consumes. Nothing downstream
   re-invents requirements.
2. **Async by default, sync only on real dependencies.** Independent work
   (backend module, QA test plan, frontend wireframe) runs in parallel
   (`async_execution=True`). Joins happen only where a real data dependency
   exists (FE integration needs API contract; unit tests need backend code +
   QA cases).
3. **Explicit context, not implicit memory.** Each task declares `context=[...]`
   pointing at the precise upstream tasks it depends on. This bounds the prompt
   surface, prevents context bleed, and makes the graph auditable.
4. **Structured handoffs — no exceptions.** *Every* task — including the
   final architect review — emits a `Pydantic` model via `output_pydantic=`.
   Human-readable artifacts (markdown review, Gradio app code) are rendered
   from the structured payload inside the task callback, never produced by
   the agent as free-form prose. This keeps the entire pipeline machine-
   verifiable end-to-end.
5. **Callbacks for side effects.** File persistence, telemetry, and
   guardrail checks run inside task `callback=` — agents never touch disk
   themselves.
6. **Hierarchical, Architect-led.** `Process.hierarchical` with the
   `architect_lead` as the `manager_agent`. Only the Architect may delegate.
   On guardrail failure (e.g., security violation flagged by a T1 callback),
   the Architect re-delegates with remediation notes — this is the entire
   reason we went hierarchical rather than sequential.
7. **Backend is a library first, an API later.** The backend ships as an
   importable Python module (`backend/` package) with a clean service-layer
   boundary. FastAPI lives behind a thin `create_app()` adapter that wraps
   the same service functions. Today the Gradio frontend calls the services
   directly in-process; tomorrow we flip a flag and run `uvicorn` without
   touching the service layer. No premature HTTP.
7. **Security & efficiency are gates, not afterthoughts.** A guardrail on the
   backend task validates: no plaintext secrets, parameterized DB access, input
   validation on every API surface, authn/authz hooks present.

---

## 2. Agent Roster

| # | Agent              | Specialty                                            | Delegation | Memory | Tools (suggested)                          |
|---|--------------------|------------------------------------------------------|------------|--------|--------------------------------------------|
| 1 | `architect_lead`   | Requirements → system design (Python + Gradio + FastAPI) | ✅ yes     | ✅     | `FileReadTool`, `WebsiteSearchTool`        |
| 2 | `backend_engineer` | FastAPI + SQLite/SQLAlchemy module, security, perf  | ❌         | ✅     | `CodeInterpreterTool`, `FileWriterTool`    |
| 3 | `frontend_engineer`| Gradio UX — modern, attractive, accessible           | ❌         | —      | `FileWriterTool`                           |
| 4 | `qa_engineer`      | Test case + acceptance criteria design               | ❌         | ✅     | `FileWriterTool`                           |
| 5 | `unit_test_engineer`| Unit + regression tests against backend module      | ❌         | —      | `CodeInterpreterTool`, `FileWriterTool`    |

Detailed prompts and personas: see [agents_design.md](./agents_design.md).

---

## 3. Task Graph

```
                              ┌──────────────────────────┐
   raw user requirements ───▶ │  T0  design_system       │   (architect_lead)
                              │  out: SystemDesign       │
                              └────────────┬─────────────┘
                                           │  context fan-out
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼ (async)                    ▼ (async)                    ▼ (async)
   ┌────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
   │ T1 build_backend   │      │ T2 design_test_plan  │      │ T3 design_frontend   │
   │ backend_engineer   │      │ qa_engineer          │      │ frontend_engineer    │
   │ out: BackendBundle │      │ out: TestPlan        │      │ out: FrontendSpec    │
   └─────────┬──────────┘      └──────────┬───────────┘      └──────────┬───────────┘
             │                            │                             │
             │  (API contract)            │ (test cases)                │ (wireframe + UX)
             ├────────────┬───────────────┘                             │
             │            │                                             │
             ▼ (sync)     ▼ (sync)                                      │
   ┌────────────────────────────────┐                                   │
   │ T4 implement_unit_tests        │                                   │
   │ unit_test_engineer             │                                   │
   │ context=[T1, T2]               │                                   │
   │ out: UnitTestSuite             │                                   │
   └─────────────────┬──────────────┘                                   │
                     │                                                  │
                     │                ┌─────────────────────────────────┘
                     │                │  (FE integrates against API contract from T1)
                     ▼                ▼
              ┌──────────────────────────────────┐
              │ T5 integrate_frontend            │  (sync)
              │ frontend_engineer                │
              │ context=[T0, T1, T3]             │
              │ out: GradioApp                   │
              └──────────────┬───────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────┐
              │ T6 architect_review              │  (sync, terminal)
              │ architect_lead                   │
              │ context=[T0, T1, T2, T4, T5]     │
              │ out: ReviewReport (markdown)     │
              └──────────────────────────────────┘
```

Legend:
- **(async)** → `async_execution=True`; CrewAI dispatches T1/T2/T3 in parallel.
- **(sync)** → ordinary task; CrewAI blocks until its declared `context` tasks
  have completed.
- Arrows are **explicit `context=` edges**, not implicit "previous task" leakage.

---

## 4. Synchronization Model

CrewAI’s async semantics: a task with `async_execution=True` is started and
the kickoff loop continues. The first downstream task that declares it in its
`context=[...]` triggers a join (await). We exploit that as follows:

| Phase | Tasks running                  | Join point                                       |
|-------|--------------------------------|--------------------------------------------------|
| 0     | T0                              | terminal — must finish before fan-out            |
| 1     | T1, T2, T3 (all async)          | implicit — none of them references the others    |
| 2     | T4 awaits {T1, T2}              | join on backend + QA artifacts                   |
| 3     | T5 awaits {T0, T1, T3}          | join on design + API contract + FE spec          |
| 4     | T6 awaits {T0, T1, T2, T4, T5}  | full join — architect sign-off                   |

Result: T1/T2/T3 truly run concurrently; T4 and T5 also run concurrently
because neither references the other (T5 depends on T1+T3, T4 on T1+T2).
Only T6 is a hard barrier.

---

## 5. Context-Flow Contract (Pydantic Schemas)

Every edge carries a typed payload. Free-form text is forbidden between
agents — only at the human-facing boundary.

```
SystemDesign            # T0 output
├── overview: str
├── modules: list[ModuleSpec]
├── data_model: list[EntitySpec]          # tables/columns/relations
├── api_contract: list[EndpointSpec]      # method, path, req, resp, authz
├── nfr: NonFunctionalRequirements        # perf, security, scalability
├── ui_spec: UISpec                       # pages, components, flows
└── risks: list[str]

BackendBundle           # T1 output  (library-first, API-ready)
├── package_name: str                     # e.g. "backend"
├── module_layout: list[FilePath]         # routers/, services/, repositories/, models/
├── service_contract: list[ServiceSpec]   # the IMPORTABLE surface (function sigs, typed)
├── api_contract_resolved: list[EndpointSpec]  # FastAPI adapter; MUST match T0.api_contract
├── adapter_entrypoint: FilePath          # backend/api.py::create_app — opt-in HTTP
├── db_schema_ddl: str
├── security_checklist: SecurityChecklist
└── notes_for_frontend: str               # which service functions FE imports

TestPlan                # T2 output
├── acceptance_criteria: list[AC]
├── test_cases: list[TestCase]            # id, given/when/then, priority
└── coverage_matrix: list[CoverageRow]    # req_id ↔ test_id

FrontendSpec            # T3 output
├── pages: list[PageSpec]
├── components: list[ComponentSpec]
├── style_tokens: StyleTokens             # palette, type, spacing
└── interaction_map: list[Interaction]

UnitTestSuite           # T4 output
├── test_files: list[FilePath]
├── coverage_estimate: float
└── regression_set: list[TestCaseId]

GradioApp               # T5 output
├── entrypoint: FilePath
├── wired_endpoints: list[EndpointBinding]
└── ux_notes: str

ReviewReport            # T6 output  (structured; markdown rendered by callback)
├── status: Literal["PASS", "PASS_WITH_NOTES", "BLOCK"]
├── contract_diff: list[ContractDiffRow]  # T0.api_contract vs T1.api_contract_resolved
├── coverage_gaps: list[RequirementId]    # requirements with no test in T2
├── regression_gaps: list[TestCaseId]     # P0 cases missing from T4.regression_set
├── security_failures: list[SecurityCheckRow]
├── wired_endpoint_gaps: list[EndpointId] # endpoints missing from T5.wired_endpoints
└── summary_markdown: str                 # human-readable rendering
```

Concrete field definitions go in `src/software_engineer_team/schemas.py`
during implementation.

---

## 6. Guardrails & Callbacks  *(locked in: retry-with-feedback model)*

We split post-task work into two distinct mechanisms, intentionally:

**Guardrails (`guardrail=` on Task)** — run *before* the task is considered
complete. If a guardrail returns failure, CrewAI re-dispatches the task to
the **same agent** with the failure detail injected into its context, up to
`max_retries`. **No downstream task starts until this task passes its
guardrail.** This is our enforcement loop — modular, per-task, with feedback.

**Callbacks (`callback=` on Task)** — run *after* a successful task. Pure
side effects: persist artifacts to disk, emit telemetry. Callbacks never
fail the task, never mutate the payload.

| Task | Guardrail (blocks until pass; feeds failure back) | Callback (side effects on success) |
|------|----------------------------------------------------|------------------------------------|
| T0   | Schema validity of `SystemDesign`; every module in `modules` referenced by at least one endpoint or UI page | Persist `output/00_system_design.json` |
| T1   | `security_guardrail` (see `knowledge/security_checklist.md` auto-rules) **+** `api_contract_resolved` reconciles to `T0.api_contract` field-for-field **+** `service_contract` covers every endpoint | Persist backend files; emit `BackendBundle` |
| T2   | Every requirement id in `SystemDesign` appears in `coverage_matrix`; every endpoint has ≥1 happy, ≥1 negative, ≥1 edge case | Persist `output/02_test_plan.json` |
| T3   | Every page in `SystemDesign.ui_spec` covered in `pages`; style tokens non-empty | Persist `output/03_frontend_spec.json` |
| T4   | `pytest --collect-only` succeeds on emitted tests; every P0 case from T2 present in `regression_set` | Persist test files |
| T5   | Every service in `T1.service_contract` has a corresponding Gradio handler; every handler maps 1:1 to a service call (no business logic in Gradio code) | Persist Gradio app files |
| T6   | `ReviewReport` schema validity (final summary; no further gating — by here every upstream task has already passed its own guardrail) | Render `summary_markdown` to `output/REVIEW.md` |

**Why no end-of-run BLOCK gate.** Because every producing task gates itself,
T6 is purely a summary. If T1’s security guardrail fails three times in a
row, the run stops at T1 — nothing downstream ever runs on broken code.
This is the whole point of the modular design + per-task unit tests.

**Retry budget.** Each guarded task gets `max_retries=3` by default. The
failure detail passed back to the agent is the **specific rule id that
failed and the offending file/line/symbol** — not a vague “try again.”
---

## 7. Crew Wiring  *(locked in)*

```
Process               = hierarchical          # decided
manager_agent         = architect_lead        # allow_delegation=True
memory                = True                  # long-term + entity
embedder              = openai/text-embedding-3-small
planning              = True                  # manager pre-plans task order
output_log_file       = output/run.log
```

Why hierarchical: the Architect must be empowered to *re-delegate* when a
guardrail in T1 callback fails (e.g., security violation). Hierarchical
process + `allow_delegation=True` on the manager gives that authority
cleanly without us having to migrate to a Flow yet.

### Backend deployment posture *(locked in)*

The backend is built as a **Python library / module**, not a running service.
The Gradio frontend imports its service layer directly and calls it
in-process. To make the future flip to a standalone API free of refactor
cost, the backend MUST be structured so:

- **Service layer is pure** — `backend/services/*.py` exposes typed
  functions (`def create_user(session, payload: UserCreate) -> User`). No
  request/response objects, no HTTP concerns, no Gradio concerns.
- **Routers are a thin shell** — `backend/api/routers/*.py` contains FastAPI
  routers that *only* parse/validate input and call into services. Generated
  alongside the library but not required at runtime.
- **Single entrypoint per posture** — `backend.create_app()` returns a
  FastAPI app when/if we want HTTP; `from backend.services import ...` is
  the today path. Both surfaces are validated against the same
  `api_contract_resolved`.
- **No FastAPI imports leak into services or repositories.** Enforced by the
  T1 security/structure guardrail (import-graph check).

---

## 8. Extension Points (Designed for Growth)

| Want to add…                       | How                                                                 |
|-----------------------------------|---------------------------------------------------------------------|
| A DevOps/Deployment agent          | Append T7 with `context=[T1, T5]`, output Dockerfile + compose      |
| A Security review agent            | Insert between T1 callback and T4 with `context=[T1]`               |
| Human-in-the-loop on design        | `human_input=True` on T0, or `@human_feedback` if migrating to Flow |
| Iterative refinement / loops       | Migrate the crew into a `Flow` with `@router` on T6.status          |
| Multiple backend languages         | Promote `backend_engineer` into a pool, select via manager planning |
| Knowledge sources (style guides)   | Attach `crewai.knowledge` sources to each agent (see knowledge/)    |
| Multimodal (mockups in)            | `multimodal=True` on `frontend_engineer`                            |

---

## 9. Failure & Recovery  *(locked in)*

- **Guardrail fails on any producing task (T1–T5)** → CrewAI re-dispatches
  the task to the same agent with the structured failure detail (rule id,
  file, line, symbol) appended to its context. The downstream graph stays
  frozen until this task passes. Up to `max_retries=3` attempts.
- **Retries exhausted** → the crew halts at that task; the failure detail
  and last attempt artifact are persisted under `output/<task>/FAILED.json`
  so you can intervene with surgical context, not a full re-run.
- **Async task exception (not a guardrail — a hard error)** → surfaces on
  the next join. Treated identically: retry up to budget, then halt.
- **Schema drift** between `T1.api_contract_resolved` and `T0.api_contract`
  is a T1 guardrail violation, not a T6 finding — it gets caught and fed
  back to `backend_engineer` immediately, not at the end of the run.

---

## 10. Directory Layout (target, not present yet)

```
3_crewai/software_engineer_team/
├── documentation/
│   ├── ARCHITECTURE.md          ← this file
│   ├── agents_design.md
│   └── tasks_design.md
├── src/software_engineer_team/
│   ├── crew.py
│   ├── schemas.py               ← all Pydantic contracts
│   ├── callbacks.py             ← task callbacks + guardrails
│   ├── config/
│   │   ├── agents.yaml
│   │   └── tasks.yaml
│   └── tools/
├── knowledge/
│   ├── user_preference.txt
│   └── security_checklist.md         ← loaded as KnowledgeSource for backend_engineer, architect_lead, unit_test_engineer
└── output/
    ├── 00_system_design.json
    ├── 01_backend/
    ├── 02_test_plan.json
    ├── 03_frontend_spec.json
    ├── 04_unit_tests/
    ├── 05_gradio_app/
    └── REVIEW.md
```
