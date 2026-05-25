# Website P0 (Playwright)

P0 website coverage runs inside **`pr-gate`** via `./bin/sentinel --<profile> website` (or the full gate).

## Scope today (J5)

Marketing-site black-box checks against `WEBSITE_BASE_URL` — no mocks:

| Spec | Flow |
|------|------|
| Homepage | Loads with visible `h1` |
| Navigation | Primary nav reaches use cases |
| Cookie banner | Accept-all flow + `localStorage` |
| Waitlist | Form visible, email input accepts text |

Tagged `@p0` in `suites/website/e2e/p0-gate.spec.ts`.

Auth, caregiver dashboard, and in-app care paths are **phase 2** — they need stable selectors and staging test users from the Website product repo.

## Run locally

```bash
# Staging or local dev server must be up
./bin/sentinel --local check-targets   # hub + website
./bin/sentinel --local website         # @p0 only
./bin/sentinel --local website --full  # all Playwright specs
```

## CI

Included in `pr-gate`. JUnit: `reports/<profile>/website-junit.xml` (merged into `junit-merged.xml`).

## Failures

`pr-gate` exits non-zero when any `@p0` spec fails. Fix the deployed site or update selectors in `suites/website/e2e/` to match staging DOM.
