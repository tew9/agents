# Task Designs

Seven tasks, four async, three synchronous joins. Each entry maps 1:1 to a
`config/tasks.yaml` block plus a `@task` method in `crew.py`. The async/sync
column is set via `async_execution=` on the Task; context edges are set via
`context=[...]`.

> **Convention:** `{requirements}` is the only kickoff input. Everything else
> flows through typed task outputs.

---

## T0 — `design_system`  (sync, terminal kickoff)

| Field             | Value |
|-------------------|-------|
| `agent`           | `architect_lead` |
| `async_execution` | `false` |
| `context`         | *(none — root)* |
| `output_pydantic` | `SystemDesign` |
| `guardrail`       | `validate_system_design` → every module referenced by ≥1 endpoint or UI page; every endpoint has explicit authz scope; every requirement id is unique |
| `max_retries`     | `3` |
| `callback`        | `persist_system_design` → writes `output/00_system_design.json` |
| `human_input`     | `false`  *(locked)* |

**Description (yaml `description`):**
> Read the user requirements: `{requirements}`. Produce a complete
> `SystemDesign`: module decomposition, data model (entities, fields,
> relations), API contract (method, path, request/response Pydantic schemas,
> authz scope per endpoint), non-functional requirements (perf, security,
> scalability targets), UI spec (pages, components, primary flows), and known
> risks. Default stack: Python 3.11+, FastAPI, SQLAlchemy 2.x + SQLite,
> Gradio. Justify any deviation. The design must be implementable by the four
> specialist engineers without further clarification.

**Expected output:** `SystemDesign` JSON (no prose).

---

## T1 — `build_backend`  (async)

| Field             | Value |
|-------------------|-------|
| `agent`           | `backend_engineer` |
| `async_execution` | `true` |
| `context`         | `[T0]` |
| `output_pydantic` | `BackendBundle` |
| `guardrail`       | `security_and_contract_guardrail` → (a) runs the **auto** rules from `knowledge/security_checklist.md` (secret regex, SQL AST, import-graph, signature scan, crypto scan); (b) reconciles `api_contract_resolved` to `T0.api_contract` field-for-field; (c) verifies every endpoint maps to a function in `service_contract`. Returns the failing rule id + file/line on failure so the agent can fix surgically. |
| `max_retries`     | `3` |
| `callback`        | `persist_backend` → writes backend files under `output/01_backend/` |
| `output_file`     | `output/01_backend/backend_bundle.json` |

**Description:**
> Implement the backend as a Python **library** at `backend/`, layered as
> `api → services → repositories → models`. Use SQLAlchemy 2.x with SQLite.
> The **service layer is the public surface** consumed by the Gradio
> frontend in-process; it must be HTTP-agnostic — no FastAPI imports outside
> `backend/api/`. Additionally produce a thin FastAPI adapter under
> `backend/api/` exposing `create_app()` and routers that call the same
> services, so the library can be promoted to an HTTP service later with
> zero changes to business logic. Use Pydantic for all schemas. No
> string-interpolated SQL. Secrets only via environment. Return a
> `BackendBundle` whose `service_contract` lists the importable surface and
> whose `api_contract_resolved` matches `SystemDesign.api_contract`
> field-for-field — any divergence must be listed in `notes_for_frontend`
> with rationale.

**Expected output:** `BackendBundle` JSON + source files written by callback.

---

## T2 — `design_test_plan`  (async)

| Field             | Value |
|-------------------|-------|
| `agent`           | `qa_engineer` |
| `async_execution` | `true` |
| `context`         | `[T0]` |
| `output_pydantic` | `TestPlan` |
| `guardrail`       | `coverage_guardrail` → every requirement id from `SystemDesign` appears in `coverage_matrix`; every endpoint has ≥1 happy-path, ≥1 negative, ≥1 edge case; test ids are unique |
| `max_retries`     | `3` |
| `callback`        | `persist_test_plan` → writes `output/02_test_plan.json` |

**Description:**
> Using `SystemDesign` (requirements, API contract, NFRs), produce a complete
> `TestPlan`. For every endpoint and every UI flow: at least one happy-path,
> one negative, and one edge case. Each test case has a stable id
> (`TC-<area>-<n>`), preconditions, steps, and expected result. Build the
> requirement↔test coverage matrix. Tag P0 cases that must be in the
> regression set.

**Expected output:** `TestPlan` JSON.

---

## T3 — `design_frontend`  (async)

| Field             | Value |
|-------------------|-------|
| `agent`           | `frontend_engineer` |
| `async_execution` | `true` |
| `context`         | `[T0]` |
| `output_pydantic` | `FrontendSpec` |
| `guardrail`       | `frontend_spec_guardrail` → every page in `SystemDesign.ui_spec` covered; style tokens (palette, type, spacing) all populated; every interaction names a target component that exists in the spec |
| `max_retries`     | `3` |
| `callback`        | `persist_frontend_spec` → writes `output/03_frontend_spec.json` |

**Description:**
> From `SystemDesign.ui_spec`, design the Gradio frontend: page list, component
> hierarchy per page, interaction map (what triggers what), style tokens
> (palette, typography scale, spacing). Aim for a modern, opinionated look —
> never the default Gradio theme. Do not write code yet.

**Expected output:** `FrontendSpec` JSON.

---

## T4 — `implement_unit_tests`  (sync join on T1, T2)

| Field             | Value |
|-------------------|-------|
| `agent`           | `unit_test_engineer` |
| `async_execution` | `false` |
| `context`         | `[T1, T2]` |
| `output_pydantic` | `UnitTestSuite` |
| `guardrail`       | `unit_test_guardrail` → `pytest --collect-only` succeeds on emitted files; every P0 case from `T2.test_cases` is present in `regression_set`; every service in `T1.service_contract` has ≥1 unit test |
| `max_retries`     | `3` |
| `callback`        | `persist_unit_tests` → writes files under `output/04_unit_tests/` |

**Description:**
> Convert `TestPlan.test_cases` into runnable `pytest` modules targeting
> `BackendBundle`. Use SQLite in-memory and FastAPI `TestClient` with
> dependency overrides — no network, no real DB. Mirror the backend module
> layout under `tests/`. Every test docstring cites its `TC-…` id. P0 cases
> go under `tests/regression/`.

**Expected output:** `UnitTestSuite` JSON + test files written by callback.

---

## T5 — `integrate_frontend`  (sync join on T0, T1, T3)

| Field             | Value |
|-------------------|-------|
| `agent`           | `frontend_engineer` |
| `async_execution` | `false` |
| `context`         | `[T0, T1, T3]` |
| `output_pydantic` | `GradioApp` |
| `guardrail`       | `frontend_integration_guardrail` → every service in `T1.service_contract` has a corresponding Gradio handler in `wired_endpoints`; each handler maps 1:1 to a single service call (no business logic in Gradio code, checked via AST); imports include `backend.services.*`, never `requests`/`httpx` (in-process today) |
| `max_retries`     | `3` |
| `callback`        | `persist_gradio_app` → writes `output/05_gradio_app/app.py` and supporting files |

**Description:**
> Build the Gradio Blocks app per `FrontendSpec`, wired to
> `BackendBundle.service_contract` — i.e., **import the backend services
> directly and call them in-process** (no HTTP today). Treat
> `api_contract_resolved` as the future contract: every Gradio handler must
> map cleanly to exactly one service call so that promoting to HTTP later
> is a 1:1 swap. Apply the style tokens via a Gradio theme + minimal custom
> CSS. Every interactive element must surface backend errors gracefully.

**Expected output:** `GradioApp` JSON + Gradio app files.

---

## T6 — `architect_review`  (sync, terminal — summary only)

| Field             | Value |
|-------------------|-------|
| `agent`           | `architect_lead` |
| `async_execution` | `false` |
| `context`         | `[T0, T1, T2, T4, T5]` |
| `output_pydantic` | `ReviewReport` |
| `output_file`     | `output/REVIEW.md`  *(rendered from `summary_markdown` by callback)* |
| `callback`        | `render_review` → writes the markdown summary; stamps version + artifact hashes |

**Description:**
> Produce the structured `ReviewReport` summarizing the run. By the time
> this task executes, every upstream task has already passed its own
> guardrail — so T6 is a **summary, not a gate**. Fill the structured
> fields (`contract_diff`, `coverage_gaps`, `regression_gaps`,
> `security_failures`, `wired_endpoint_gaps`) for the record; under normal
> conditions they will be empty. Set `status=PASS` unless a `PASS_WITH_NOTES`
> condition (e.g., informational coverage gap on a non-functional
> requirement) applies. Fill `summary_markdown` with a concise human
> review: what was built, what tests cover it, what to verify manually,
> and what to do next.

**Expected output:** `ReviewReport` pydantic; markdown rendered by callback.

---

## Dynamic Callback & Guardrail Signatures (reference)

Guardrails enforce correctness; callbacks persist artifacts. Same signature
shape for testability.

```python
# Guardrail — runs BEFORE the task completes; failure triggers retry-with-feedback.
def guardrail(task_output: TaskOutput) -> tuple[bool, str]:
    # return (True, "")           on success
    # return (False, detail_msg)  on failure; `detail_msg` is fed back
    #                              into the agent's context for the retry
    ...

# Callback — runs AFTER a successful task; pure side effects.
def callback(task_output: TaskOutput) -> None:
    # task_output.pydantic  → the typed payload (when output_pydantic set)
    # task_output.raw       → raw string
    # task_output.agent     → agent role that produced it
    # side effects only; never mutate the payload
    ...
```

Recommended files:
- `src/software_engineer_team/guardrails.py` — all `*_guardrail` functions.
- `src/software_engineer_team/callbacks.py` — all `persist_*` and
  `render_*` callbacks.

---

## YAML Skeleton (drop-in for `config/tasks.yaml`)

> Reference only — final schemas/imports happen during implementation.

```yaml
design_system:
  description: >
    Read the user requirements: {requirements}. Produce a complete SystemDesign...
  expected_output: >
    A SystemDesign JSON object conforming to the schema in schemas.py.
  agent: architect_lead

build_backend:
  description: >
    Implement the backend module described in SystemDesign...
  expected_output: >
    A BackendBundle JSON object; source files persisted by callback.
  agent: backend_engineer
  async_execution: true
  context: [design_system]

design_test_plan:
  description: >
    Produce a complete TestPlan from SystemDesign...
  expected_output: >
    A TestPlan JSON object.
  agent: qa_engineer
  async_execution: true
  context: [design_system]

design_frontend:
  description: >
    Design the Gradio frontend from SystemDesign.ui_spec...
  expected_output: >
    A FrontendSpec JSON object.
  agent: frontend_engineer
  async_execution: true
  context: [design_system]

implement_unit_tests:
  description: >
    Convert TestPlan.test_cases into runnable pytest modules...
  expected_output: >
    A UnitTestSuite JSON object; test files persisted by callback.
  agent: unit_test_engineer
  context: [build_backend, design_test_plan]

integrate_frontend:
  description: >
    Build the Gradio Blocks app per FrontendSpec, wired to BackendBundle...
  expected_output: >
    A GradioApp JSON object; app files persisted by callback.
  agent: frontend_engineer
  context: [design_system, build_backend, design_frontend]

architect_review:
  description: >
    Audit deliverables against SystemDesign and emit a structured ReviewReport...
  expected_output: >
    A ReviewReport JSON object with status PASS | PASS_WITH_NOTES | BLOCK; markdown rendered by callback.
  agent: architect_lead
  context: [design_system, build_backend, design_test_plan, implement_unit_tests, integrate_frontend]
  output_file: output/REVIEW.md
```

---

## Decisions Locked In

- ✅ **Process:** `hierarchical`, `architect_lead` is the `manager_agent`.
- ✅ **Structured output on every task** (`output_pydantic=` set for T0–T6,
   including the architect review). Markdown / source files are rendered
   from structured payloads in callbacks, never produced as free-form agent
   prose.
- ✅ **Backend posture:** library-first (`backend/` package, pure service
   layer), with a thin FastAPI adapter (`backend/api/create_app()`) shipped
   alongside so promoting to an HTTP service later is a flag flip, not a
   refactor. Frontend imports services directly today.
- ✅ **No human-in-the-loop.** `human_input=false` on every task. The crew
   runs end-to-end autonomously.
- ✅ **Knowledge sources:** `knowledge/security_checklist.md` is the
   authoritative security spec, loaded for `backend_engineer`,
   `architect_lead`, and `unit_test_engineer`. No Gradio guide — the
   frontend agent uses its own knowledge of modern Gradio design.
- ✅ **Failure model:** per-task `guardrail=` + `max_retries=3`. Failures
   are fed back to the same agent with structured detail (rule id, file,
   line). Downstream tasks never start on broken upstream output. No
   end-of-run BLOCK gate — T6 is summary only.

