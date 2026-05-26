# Backend Security Checklist (Module-Based Python)

> **Scope:** A Python `backend/` library (pure service layer + optional
> FastAPI adapter). The frontend imports services in-process today; the same
> code may be promoted to an HTTP service later. **Every item below applies
> to the library surface, not just the HTTP surface** — an input is an
> input whether it arrives via Gradio or via `requests`.
>
> **Use:** This file is loaded as a CrewAI knowledge source for
> `backend_engineer`, `architect_lead`, and `unit_test_engineer`. The T1
> `security_guardrail` task guardrail mechanically validates the items
> marked **(auto)**; items marked **(review)** are checked by `architect_lead`
> in T6.

---

## 1. Input Validation
- **(auto)** Every public service function accepts a Pydantic model **or**
  primitives with explicit type hints. No `**kwargs`, no untyped `dict`
  inputs on the public surface.
- **(auto)** Pydantic models for inputs use `model_config = ConfigDict(extra="forbid")`.
- **(review)** Numeric/string fields declare bounds (`ge`, `le`, `max_length`)
  wherever a real-world bound exists.
- **(review)** Path/filename inputs are normalized and confined under a
  whitelisted base directory (no `..` traversal).

## 2. SQL & Persistence
- **(auto)** Zero string interpolation or f-strings in SQL. All queries go
  through SQLAlchemy ORM or `text()` with bound parameters.
- **(auto)** No `eval`, `exec`, `pickle.loads` on data that crossed an input
  boundary.
- **(review)** Database session is created per request/operation and closed
  (context manager or dependency); no module-global open session.
- **(review)** Migrations / `Base.metadata.create_all` only run from an
  explicit init entrypoint, never on import.

## 3. Authn / Authz
- **(auto)** Every service that mutates state takes a `current_user` (or
  equivalent principal) argument — even if it is a stub today. No silent
  "anyone can call this" mutations.
- **(review)** Authorization is checked at the **service** layer, not only
  at the router. The router is a thin shell; the library is the security
  boundary.
- **(review)** Read endpoints that return user-scoped data filter by the
  principal at the repository call site, not after fetching.

## 4. Secrets & Configuration
- **(auto)** No literal secrets (API keys, tokens, passwords, connection
  strings with creds) in source. Detected by regex: `(?i)(api[_-]?key|secret|token|password)\s*=\s*["'][^"']+["']`.
- **(auto)** All configuration loaded via `pydantic_settings.BaseSettings`
  reading from environment; no `os.getenv` scattered through services.
- **(review)** `.env` files are gitignored; example values live in `.env.example`.

## 5. Module Boundaries (Library-First Posture)
- **(auto)** No `from fastapi`, `from starlette`, `import fastapi` anywhere
  outside `backend/api/`. Services and repositories are HTTP-agnostic.
- **(auto)** No `import gradio` anywhere in `backend/`. The frontend
  depends on the backend, never the reverse.
- **(review)** `backend/services/` does not import from `backend/api/`
  (one-way dependency).

## 6. Errors & Logging
- **(auto)** No bare `except:` and no `except Exception: pass`.
- **(review)** Exceptions raised to callers are typed (custom exception
  classes per domain) and never leak SQL fragments, file paths, or
  stack traces of internals.
- **(review)** Logging uses the `logging` module (no `print` in services).
  PII / secrets are never logged.

## 7. Cryptography & Hashing
- **(auto)** No `md5` or `sha1` for passwords or auth tokens. Use `bcrypt`,
  `argon2`, or `hashlib.pbkdf2_hmac` (≥200k iters).
- **(auto)** No `random.random` / `random.choice` for tokens/IDs. Use
  `secrets` module.

## 8. Output / Serialization
- **(review)** Response models are explicit Pydantic schemas — never return
  ORM objects directly from the public surface (prevents accidental
  exposure of password hashes, internal flags, etc.).
- **(review)** Datetime fields are timezone-aware (UTC).

## 9. Concurrency & Resource Safety
- **(review)** Long-running or external calls are wrapped with a timeout.
- **(review)** No global mutable state in services (use the session/store
  passed in, or a typed dependency object).

## 10. Test Surface
- **(auto)** Every service function in `service_contract` has at least one
  unit test in T4. Enforced by coverage cross-reference.

---

## Auto-Check Summary (T1 guardrail)

The `security_guardrail` callable runs in this order and fails the task
(with the specific violation appended to the agent's retry context) on the
first failure:

1. Regex scan for hardcoded secrets (rule 4.1).
2. AST scan for string-interpolated SQL and dangerous calls (rules 2.1, 2.2, 6.1).
3. Import-graph scan — forbidden imports outside allowed packages (rules 5.1, 5.2, 5.3).
4. Public-surface signature scan — every service has typed inputs and a
   `current_user`-like principal where it mutates (rules 1.1, 3.1).
5. Crypto scan — forbid `md5`/`sha1` on auth paths, forbid `random.*` for
   token generation (rules 7.1, 7.2).

If any check fails, the task is re-dispatched to `backend_engineer` with
the failure detail and the offending file/line.
