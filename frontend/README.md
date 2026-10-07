# casemap frontend (SP-3)

Responsive React SPA for [casemap](https://github.com/anomalyco/casemap) — talks
to the FastAPI server (SP-2) over Bearer-authenticated REST.

## Stack

- **Vite** + **React 18** + **TypeScript** (strict mode)
- **shadcn/ui** + **Tailwind CSS** — components live in `src/components/ui/`
- **TanStack Query** — server state
- **react-router-dom v6** — routing
- **react-hook-form** + **zod** — forms
- **Vitest** + **axe-core** — unit + a11y tests
- **lucide-react** — icons

## Quick start

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:5173
```

The Vite dev server proxies `/api/*` to the FastAPI server
(`http://127.0.0.1:8765` by default — adjust in `vite.config.ts`).

```bash
# In a separate terminal, from the repo root:
uv run casemap serve
```

## Scripts

| Command | What |
| --- | --- |
| `pnpm dev` | Start Vite dev server with HMR |
| `pnpm build` | Type-check + production build |
| `pnpm preview` | Serve the production build locally |
| `pnpm typecheck` | `tsc --noEmit` |
| `pnpm lint` | ESLint (`.ts`/`.tsx`) |
| `pnpm test` | Vitest in CI mode (single run) |

## Project layout

```
src/
  components/
    ui/         shadcn/ui primitives (button, card, dialog, …)
    layout/     Header, Sidebar, Shell
    brain-map/  BrainMap SVG + CaseNode + CaseDetail + StatusControls
    shared/     StatusBadge, EmptyState, ErrorBoundary, TypeBadge
    providers/  ApiProvider (token context)
  hooks/        TanStack Query hooks + theme
  lib/          api client, types, queryClient, utils
  pages/        Home, NewProject, Project, Cases, Progress, Report
  styles/       Tailwind globals + CSS variable theme tokens
tests/
  components/   Unit tests for individual components
  pages/        Page integration tests (mocked API)
  a11y/         axe-core checks (jsdom)
```

## Design tokens

CSS variables in `src/styles/globals.css` define semantic colors for
`--background`, `--foreground`, `--primary`, plus casemap-specific:

- `--status-{pending,in-progress,passed,failed,blocked,skipped}` — node outline + badge text
- `--case-{positive,negative,edge,security}` — node fill

Dark mode is the default (`<html class="dark">`); manual toggle in the header
persists to `localStorage` (`casemap-theme`).

## Accessibility

- Keyboard navigation throughout (focus rings, `tabindex`, `aria-pressed`)
- `aria-live="polite"` on progress percentages
- Status buttons expose `aria-label` and `aria-pressed`
- `prefers-reduced-motion` honored — animations collapsed to 0.01ms
- Contrast ratios ≥ 4.5:1 in both themes (verified manually; `color-contrast`
  axe rule disabled in jsdom where it can't compute)

## Notes

- This package is independent of the Python repo — it talks to it over HTTP.
- Token storage uses `localStorage` (key `casemap-token`). Switch to a real
  auth flow when adding SSO / multi-user accounts.
