# Sentinel

Black-box live regression harness for HomeCareGuardian (hub / website / iOS). See
[`README.md`](README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and
[`docs/run-local.md`](docs/run-local.md) for full docs. There is **no product
source and no server in this repo** — Sentinel only probes already-deployed HCG
surfaces over live HTTP/UI. The only runnable code here is the `./bin/sentinel`
CLI plus its pytest/Playwright suites.

## Cursor Cloud specific instructions

Setup (`python3 -m venv .venv` + `pip install -e ".[dev]"`) is handled by the
update script; the system package `python3.12-venv` is required to create the
venv. Node 22 is used only by the website suite.

- **Activate the venv before running full gates.** `./bin/sentinel journeys`
  auto-prefers `.venv/bin/pytest`, but the `contract`, `bootstrap`, and `ios`
  steps (and therefore `pr-gate` / `pr-gate-hub`) shell out to `python3` from
  `PATH`. Without an active venv those steps fail with `ModuleNotFoundError: httpx`
  (system `python3` has no deps). Run `source .venv/bin/activate` first.
- **No live hub/website exists in the cloud VM.** Commands that need a target
  (`check-targets`, `bootstrap`, `contract`, `journeys`, `website`, `ios`,
  `pr-gate`, `pr-gate-hub`) require a reachable `HUB_BASE_URL` (and, for
  `pr-gate`/`website`, `WEBSITE_BASE_URL`). To exercise the gate end-to-end
  without real hardware, point `config/targets.local.env` at a local hub
  implementing the routes in `contracts/hub_api_catalog.yaml` and set
  `HUB_TRANSPORT=direct`. Config files under `config/targets.*.env` are
  gitignored (created from the `*.env.example` templates; the CLI falls back to
  the examples when no config is present).
- **Offline-safe (no target needed):** `./bin/sentinel help`,
  `./bin/sentinel --local target`, and `pytest suites/core --collect-only`.
- **Website suite** (`./bin/sentinel website`) auto-runs `npm ci`/`npm install`
  and `playwright install chromium` in `suites/website/`, then runs the `@p0`
  Playwright specs against `WEBSITE_BASE_URL` — it needs a live HCG marketing
  site.
- **iOS**: `ios` is an HTTP checklist against the hub; `ios-xcuitest` needs
  macOS + Xcode and is skipped unless `XCUITEST_ENABLED=1`. The relay runner
  skips unless `RELAY_BASE_URL` is set.
- **500 is never a pass** — any 500 fails the gate by design (see README).
- JUnit reports and summaries land under `reports/<profile>/`.
