# Changelog

All notable changes to casemap are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## v1.0.0 (2026-10-07) — feature-complete for the original spec

- **fix(server):** `Case.id` now scoped per project so two projects can upload
  the same spec without a primary-key conflict. Public API exposes
  `stable_id` (content-derived, BLAKE2b) under `id` and the row PK under
  `db_id`; renderer still keys by stable_id.
- **docs:** polished root README with badges, three install modes
  (CLI / Server / Web), Docker quick-start, architecture diagram, roadmap.
- **ops:** `Dockerfile` (python:3.11-slim + uv) and `docker-compose.yml`
  with named volume for SQLite persistence and HTTP healthcheck.
- **tests:** new runnable end-to-end script `tests/server/test_e2e.py`
  that boots the server, drives a two-project full pipeline, and asserts
  progress isolation.

## v0.4.0 (2026-09-21) — SP-3 responsive React frontend

- **feat(frontend):** React 18 + Vite + shadcn/ui SPA in `frontend/`
- **feat(projects):** project list, new-project form, brain-map page
  with zoom / pan / filter / search
- **feat(cases):** table view with sort + filter + dialog detail
- **feat(progress):** rollup dashboard with per-tag progress bars
- **feat(report):** server-rendered report page (iframe + print + Markdown)
- **feat(ci):** dotenv-style `.env` driven config; proxied `/api/*` in dev
- **tests:** 18 vitest tests, including axe-core a11y scan on the
  ProjectPage shell
- **build:** production bundle gzipped to ~150 KB JS + 6 KB CSS

## v0.3.0 (2026-09-21) — SP-2 FastAPI server

- **feat(server):** `casemap serve` command (FastAPI + SQLAlchemy +
  SQLite)
- **feat(routers):** `/projects`, `/specs`, `/graphs`, `/cases`,
  `/statuses`, `/ci` — six routers, all under `/api/v1`
- **feat(auth):** Bearer-token projects, one-shot API key on creation,
  admin token via `CASEMAP_SERVER_ADMIN_TOKEN`
- **feat(ci):** `POST /ci/report` accepts `matched_case_id` + status;
  writes status rows with `source=ci`
- **feat(statuses):** bulk import / export for cross-device sync
- **fix(renderers):** inline SVG used in DB-stored HTML so the report
  page renders without external assets
- **tests:** routers, services, smoke (TestClient against in-memory
  SQLite) + 5 schema tests

## v0.2.0 (2026-09-21) — SP-5 important + minor fixes

- **fix(resume):** `resume` subcommand now fails fast with a clear
  message instead of a half-render
- **fix(parsers):** Prance resolver handles missing `$ref` gracefully
- **fix(renderers):** HTML self-contained report honors disabled
  status controls
- **fix(cli):** `--llm` without `CASEMAP_LLM_API_KEY` exits non-zero
- **fix(logging):** `CASEMAP_LOG_LEVEL` honored at every level
- **chore:** 6 minor lint / typing cleanups

## v0.1.1 (2026-09-21) — SP-5 critical XSS + 5 important fixes

- **fix(security):** patches 2 critical XSS via case titles in the
  inline SVG (renderer now XML-escapes every dynamic attribute)
- **fix(parsers):** OpenAPI parser no longer crashes on `$ref` to
  definitions outside the spec
- **fix(generators):** structural generator's auth-check rule no
  longer emits duplicate cases when an endpoint has multiple security
  schemes
- **fix(renderers):** Markdown decision table sorts cases by
  endpoint, then by type — deterministic across re-runs
- **fix(cli):** invalid `spec.json` exits with a clear `Invalid: …`
  message instead of a stack trace
- **fix(ci):** deterministic progress aggregation when a project has
  zero cases (no `ZeroDivisionError`)

## v0.1.0 (2026-09-21) — SP-1 core engine

- **feat(parsers):** OpenAPI / Swagger (via `prance`), Postman v2.1,
  Apifox (delegates to OpenAPI). Auto-detection via `ParserRegistry`.
- **feat(models):** `Endpoint`, `Parameter`, `Response`, `TestCase`,
  `TestStep`, `TestGraph` (pydantic v2). BLAKE2b content-derived
  `stable_id` for reproducible case IDs.
- **feat(generators):** structural generator with 7 heuristic rules
  (happy / required / 404 / auth / conflict / boundary /
  delete-security) + property-based tests. Optional functional
  generator (LLM via OpenAI-compatible provider, disk cache).
  Pipeline orchestrator with LLM-failure → structural fallback.
- **feat(renderers):** inline SVG, self-contained HTML with localStorage
  status persistence, JSON round-trip, Markdown decision table,
  read-only report HTML with failure notes + stats.
- **feat(llm):** single-model config + OpenAI-compat provider (works
  with OpenAI, DeepSeek, Moonshot, Qwen, Zhipu, Ollama) + on-disk cache
- **feat(cli):** `casemap generate / parsers / validate / resume`
- **docs:** initial README + `examples/petstore_swagger.json`
- **tests:** integration tests across the parsers → generators →
  renderers pipeline