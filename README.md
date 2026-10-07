# casemap

<!-- Logo placeholder: drop a 256x256 PNG/SVG at docs/logo.png and the line below will pick it up -->
<p align="center">
  <img src="docs/logo.png" alt="casemap logo" width="120" />
</p>

<p align="center">
  <strong>Turn an API spec into a self-contained test-case brain map your QA team can actually use.</strong>
</p>

<p align="center">
  <a href="https://github.com/anomalyco/casemap/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" /></a>
  <img alt="Version" src="https://img.shields.io/badge/version-v1.1.0-blue" />
  <a href="https://github.com/anomalyco/casemap/actions/workflows/python-test.yml"><img alt="CI" src="https://github.com/anomalyco/casemap/actions/workflows/python-test.yml/badge.svg" /></a>
  <img alt="Python tests" src="https://img.shields.io/badge/python%20tests-236%20passed-brightgreen" />
  <img alt="Frontend tests" src="https://img.shields.io/badge/frontend%20tests-26%20passed-brightgreen" />
</p>

<p align="center">
  <a href="docs/user-guide/README.md"><img alt="📖 用户文档（QA/PM）" src="https://img.shields.io/badge/%F0%9F%93%96%20%E7%94%A8%E6%88%B7%E6%96%87%E6%A1%A3-中文-blue?style=for-the-badge" /></a>
</p>

<p align="center">
  <strong>📖 用户文档：</strong>
  <a href="docs/user-guide/README.md">中文用户指南</a>
  ·
  <a href="docs/user-guide/quickstart-offline.md">离线模式</a>
  ·
  <a href="docs/user-guide/quickstart-team.md">团队模式</a>
  ·
  <a href="docs/user-guide/tester-workflow.md">QA 工作流</a>
  ·
  <a href="docs/user-guide/pm-workflow.md">PM 工作流</a>
  ·
  <a href="docs/user-guide/troubleshooting.md">故障排查</a>
</p>

## One-liner

casemap parses OpenAPI / Swagger / Postman / Apifox JSON, generates a
self-contained HTML file with an inline SVG brain map of test cases, and lets
non-technical testers click through and mark pass / fail — without installing a
backend, a CDN, or a frontend framework.

## Three install modes

| Mode | When to use it | What you get |
|------|---------------|--------------|
| **CLI** | Solo work, one-off reviews, email-friendly output. | A single `.html` file you can email or open from a USB stick. |
| **Server** | Multi-device sync, CI integration, persistent history. | FastAPI + SQLite REST API; states live in a DB, not a browser. |
| **Web** | Multiple stakeholders browsing the same project in real time. | React + Vite + shadcn/ui SPA on top of the server. |

The three modes stack: the server stores everything, the web frontend talks to
it, and the CLI can either generate standalone HTML *or* push the same spec
into the server's DB.

---

## Quick start — CLI

```bash
git clone https://github.com/anomalyco/casemap
cd casemap
uv sync

# Try the bundled sample
uv run casemap generate examples/petstore_swagger.json -o cases.html
open cases.html           # macOS — or just double-click the file
```

You'll get an interactive SVG brain map with status controls, progress bar,
and JSON export/import buttons. Nothing leaves your machine.

## Quick start — Server

```bash
uv run casemap serve --host 0.0.0.0 --port 8765 --db ./casemap.db
# Browse the auto-generated docs at http://127.0.0.1:8765/docs
```

Minimal API flow:

```bash
BASE=http://127.0.0.1:8765/api/v1

# 1. Create a project (save the API key — it's not recoverable)
curl -sX POST $BASE/projects -H "Content-Type: application/json" \
  -d '{"name":"petstore"}' | tee project.json

PID=$(jq -r .id project.json)
KEY=$(jq -r .project_api_key project.json)

# 2. Upload a spec → server parses, generates the brain map, persists
curl -sX POST $BASE/projects/$PID/specs \
  -H "Authorization: Bearer $KEY" \
  -F "file=@examples/petstore_swagger.json" -F "format=openapi"

# 3. Fetch HTML / SVG / progress — see /docs for everything
```

For a fully scripted version of this flow, run `python tests/server/test_e2e.py`.

## Quick start — Web

```bash
# Terminal A — backend
uv run casemap serve

# Terminal B — frontend dev server
cd frontend
pnpm install
pnpm dev               # http://localhost:5173
```

The Vite dev server proxies `/api/*` to the backend. For production:

```bash
pnpm build             # tsc + vite → frontend/dist/
```

Pages: `/` (project list), `/projects/:id` (brain map), `/projects/:id/cases`
(table), `/projects/:id/progress` (rollup), `/projects/:id/report` (printable).

## Quick start — Docker

```bash
docker build -t casemap:1.0.0 .
docker compose up       # binds 8765, persists DB on named volume
```

Then point your browser at `http://localhost:8765`. Healthcheck is wired up.

---

## Architecture

```
┌───────────────────────────┐
│  parsers/                 │   OpenAPI · Postman · Apifox
│   OpenAPI (prance)        │   → list[Endpoint]
│   Postman v2.1            │
│   apifox (delegates openapi)│
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  generators/              │
│   structural  ──────────┐ │   7 heuristic rules
│   (happy/required/404/  │ │   (positive / negative / edge / security)
│    auth/conflict/bound/ │ │
│    delete-security)     │ │
│   functional ──────────┘ │   LLM rewrite → business language
│   (OpenAI-compat)        │   (optional; falls back on error)
│   pipeline               │   orchestrates structural → functional
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  renderers/               │
│   SVG  (inline)           │   <-- inside the self-contained .html
│   HTML (self-contained)   │
│   Markdown decision table │
│   JSON round-trip         │
│   Report HTML (read-only) │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│  server/ (SP-2)           │   FastAPI · SQLAlchemy · SQLite
│   Bearer-token projects   │   Bearer-token projects
│   Specs / Graphs / Cases  │   CI webhook (matched_case_id → status)
│   Statuses import/export  │   Per-project stable_id namespace
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│  frontend/ (SP-3)         │   React 18 · Vite · shadcn/ui · TS
│   BrainMap (SVG + zoom)   │   tanstack/react-query · zod · react-hook-form
│   Progress dashboard      │   18 vitest tests · axe-core a11y
│   Table view · Report     │
└───────────────────────────┘
```

Each layer is a protocol — swap any one without touching the others:

| Want to… | Add |
|---------|-----|
| Parse a new spec format | `Parser` impl + `ParserRegistry.register(...)` |
| Use a different LLM | `LLMProvider` impl, pass to `GenerationPipeline(llm=...)` |
| Add a renderer | impl with `render(graph) -> str` |
| Talk to the DB from your own tool | REST API at `/api/v1/...` |

---

## Features

- **Self-contained HTML** — open from email, USB, `curl http://...`; zero CDN, zero install.
- **Inline SVG brain map** — no Mermaid, ~30 KB; renders offline, scalable, accessible.
- **Stable case IDs (BLAKE2b)** — re-running on the same spec maps statuses 1:1.
- **Multi-project namespace** — `Case.id` is scoped per project; uploading the same spec to two projects doesn't collide.
- **CI webhook** — POST `matched_case_id` + status from your CI runner, server updates with `source=ci`.
- **Cross-device sync** — `POST /statuses/export` downloads a portable JSON, `POST /statuses/import` merges it back.
- **LLM rewrite, optional** — turn "missing required param" into "user can submit without required field"; auto-falls-back on any error.
- **Read-only report HTML** — share with stakeholders; no status controls, just progress + failure reasons.
- **Web frontend** — brain map with zoom/pan/filter/search; table view; progress dashboard; printable report; keyboard accessible.
- **Docker** — single command to ship; named volume for DB persistence; healthcheck.

---

## Roadmap

- **v1.1** — authn via OIDC (currently bearer tokens only); per-user audit log
- **v1.2** — PostgreSQL backend option (SQLite stays default); Alembic migrations
- **v1.3** — Postman + Apifox CI templates; built-in report scheduling
- **v1.4** — multi-tenant casemap cloud (hosted) — separate repo

See `docs/ROADMAP.md` (or the GitHub Project board) for the full list.

---

## Development

```bash
uv sync                    # Python deps
cd frontend && pnpm install
uv run pytest -q          # 228 Python tests
cd frontend && pnpm vitest run        # 18 frontend tests
cd frontend && pnpm tsc --noEmit        # typecheck
cd frontend && pnpm build             # production build
python tests/server/test_e2e.py       # full curl-equivalent E2E
```

The Python tests cover parsers, generators, renderers, and the FastAPI server
(in-memory SQLite + httpx TestClient). The frontend tests cover utilities,
components, and an axe-core a11y scan. `test_e2e.py` is a runnable script
(not a pytest test) that boots `casemap serve` in a subprocess and drives
the full HTTP pipeline.

## Contributing

1. Fork the repo.
2. Branch off `master`: `git switch -c feat/short-description`
3. Make the smallest diff that fixes the bug / adds the feature.
4. Add a regression test (one is enough).
5. `uv run pytest -q && cd frontend && pnpm vitest run` must stay green.
6. Open a PR.

Bug reports and spec-format quirks: please attach a redacted sample spec.
LLM output bugs: include the `--llm --model` combo and a 1-line repro.

## License

[MIT](LICENSE)