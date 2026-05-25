#!/usr/bin/env bash
# Phase 2 — XCUITest against HomeCareGuardian iOS-App (macOS + Xcode only).
set -euo pipefail

SENTINEL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HCG_IOS_APP_PATH="${HCG_IOS_APP_PATH:-}"
SCHEME="${XCUITEST_SCHEME:-HomeCareGuardian}"
DEST="${XCUITEST_DESTINATION:-platform=iOS Simulator,name=iPhone 16}"
PROFILE="${E2E_TARGET:-local}"
REPORTS_DIR="${E2E_REPORTS_DIR:-${SENTINEL_ROOT}/reports/${PROFILE}}"
RESULT_BUNDLE="${REPORTS_DIR}/ios-xcuitest.xcresult"
JUNIT_OUT="${REPORTS_DIR}/ios-xcuitest-junit.xml"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "SKIP: XCUITest requires macOS (current: $(uname -s))" >&2
  exit 0
fi

if [[ -z "${HCG_IOS_APP_PATH}" || ! -d "${HCG_IOS_APP_PATH}" ]]; then
  echo "SKIP: set HCG_IOS_APP_PATH to an iOS-App checkout (see suites/ios/README.md)" >&2
  exit 0
fi

WORKSPACE=""
PROJECT=""
if [[ -f "${HCG_IOS_APP_PATH}/HomeCareGuardian.xcworkspace/contents.xcworkspacedata" ]]; then
  WORKSPACE="${HCG_IOS_APP_PATH}/HomeCareGuardian.xcworkspace"
elif [[ -f "${HCG_IOS_APP_PATH}/${SCHEME}.xcworkspace/contents.xcworkspacedata" ]]; then
  WORKSPACE="${HCG_IOS_APP_PATH}/${SCHEME}.xcworkspace"
elif [[ -f "${HCG_IOS_APP_PATH}/${SCHEME}.xcodeproj/project.pbxproj" ]]; then
  PROJECT="${HCG_IOS_APP_PATH}/${SCHEME}.xcodeproj"
else
  echo "FAIL: no .xcworkspace or ${SCHEME}.xcodeproj under ${HCG_IOS_APP_PATH}" >&2
  exit 1
fi

mkdir -p "${REPORTS_DIR}"
rm -rf "${RESULT_BUNDLE}"

echo "==> XCUITest scheme=${SCHEME} dest=${DEST}"
echo "    app path: ${HCG_IOS_APP_PATH}"
echo "    results:  ${RESULT_BUNDLE}"

XCB_ARGS=(
  -scheme "${SCHEME}"
  -destination "${DEST}"
  -resultBundlePath "${RESULT_BUNDLE}"
  test
)

if [[ -n "${WORKSPACE}" ]]; then
  xcodebuild -workspace "${WORKSPACE}" "${XCB_ARGS[@]}"
else
  xcodebuild -project "${PROJECT}" "${XCB_ARGS[@]}"
fi

if command -v xcresulttool >/dev/null 2>&1; then
  xcresulttool get test-results tests --path "${RESULT_BUNDLE}" --format junit > "${JUNIT_OUT}" 2>/dev/null \
    || echo "WARN: could not export JUnit from xcresult (install Xcode 15+ xcresulttool)" >&2
fi

echo "==> XCUITest complete"
