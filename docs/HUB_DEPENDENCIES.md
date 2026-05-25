# Hub-side dependencies (outside Sentinel)

These items are tracked on [project #13](https://github.com/orgs/HomeCareGuardian/projects/13) but require fixes in the **hcg / hcg-core hub** deployment, not in this repo.

Sentinel keeps tests green where possible (HTTP probe fallback, allowed status codes) until the hub is fixed.

## `/openapi.json` returns 500 ([#6](https://github.com/HomeCareGuardian/sentinel/issues/6))

**Impact:** Strict OpenAPI contract comparison cannot run; `contracts/check_live_openapi.py` falls back to probing manifest paths over HTTP.

**Fix (hub repo):** Restore a valid OpenAPI document at `GET /openapi.json`.

**Sentinel follow-up after hub fix:** Set `STRICT_OPENAPI=1` in CI or `config/targets.env` to fail the contract step when OpenAPI is broken.

## ML GET endpoints return 500 on production Pi ([#7](https://github.com/HomeCareGuardian/sentinel/issues/7))

**Affected paths (examples):**

- `/api/admin/ml/status`
- `/api/ml/engine/state`, `/api/ml/scheduler/status`, `/api/ml/predictions`
- `/api/ml/activity/summary`, `/api/ml/insights/detailed`, `/api/ml/entities`
- `/api/ml/human-events/status`, `/api/ml/household-profile`
- `/api/ml/analytics-settings`, `/api/ml/relay-settings`, `/api/ml/human-events/predict`

**Impact:** Catalog tests accept `500`/`503` in `contracts/hub_api_catalog.yaml` so P0 does not fail while ML is down.

**Fix (hub repo):** ML service healthy on Pi/staging (containers, config, dependencies).

**Sentinel follow-up after hub fix:** Tighten `expect` codes in `hub_api_catalog.yaml` to `200` (and `401`/`403` where auth applies).

## Filing hub work

Open or link issues in the hub product repository, then close Sentinel issues #6 and #7 when staging/Pi returns stable responses.
