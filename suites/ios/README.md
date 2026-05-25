# iOS regression (Sentinel)

## Phase 1 — Hub HTTP smoke (P0, default)

`run_hub_e2e.py` probes P0 hub REST paths against `HUB_BASE_URL`. No simulator, no app binary.

```bash
./bin/sentinel --local ios
# or as part of pr-gate / pr-gate-hub (hub-only gate includes ios HTTP)
```

## Phase 2 — XCUITest (optional, macOS)

UI black-box tests run against a checkout of the **HomeCareGuardian iOS-App** repo on a Mac with Xcode.

### Prerequisites

- macOS with Xcode and iOS Simulator
- Clone [iOS-App](https://github.com/HomeCareGuardian/iOS-App) (or your fork)
- Staging hub reachable from the simulator host (same `HUB_BASE_URL` / deep link config as the app)

### Run

```bash
export HCG_IOS_APP_PATH=/path/to/iOS-App
export HUB_BASE_URL=https://your-staging-hub:8080   # from targets profile
./suites/ios/run_xcuitest.sh
```

Or via Sentinel when enabled:

```bash
export HCG_IOS_APP_PATH=/path/to/iOS-App
export XCUITEST_ENABLED=1
./bin/sentinel --gcp ios-xcuitest
```

### Scheme and destination

Override defaults if your project differs:

| Variable | Default |
|----------|---------|
| `XCUITEST_SCHEME` | `HomeCareGuardian` |
| `XCUITEST_DESTINATION` | `platform=iOS Simulator,name=iPhone 16` |

### CI

Default GitHub Actions runners are Linux — XCUITest is **not** in `pr-gate`. Use:

- A **macOS** self-hosted runner, or
- Manual `workflow_dispatch` job (future), or
- Release validation on a developer Mac before ship

JUnit from phase 2 is written to `reports/<profile>/ios-xcuitest-junit.xml` when `E2E_REPORTS_DIR` is set.

### Reporting

Phase 1 does not emit JUnit today; phase 2 does when Xcode exports results. Both are merged by `scripts/merge_junit.py` when present under `reports/<profile>/`.
