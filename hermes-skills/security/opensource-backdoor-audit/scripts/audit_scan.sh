#!/usr/bin/env bash
# Open-source backdoor audit scanner — one-shot grep sweep with good-list filters.
# Usage: bash audit_scan.sh <repo-path>
set -uo pipefail
REPO="${1:?usage: bash audit_scan.sh <repo-path>}"
cd "$REPO" || exit 1

EXT=(-include="*.rs" -include="*.ts" -include="*.tsx" -include="*.js" -include="*.cjs" -include="*.json" -include="*.toml" -include="*.nsh" -include="*.yml" -include="*.yaml")
EXCL=(--exclude-dir=node_modules --exclude-dir=target --exclude-dir=.git --exclude-dir=dist --exclude-dir=build)

echo "===== [1] GIT PROVENANCE ====="
git remote -v 2>/dev/null | head -5
echo "commits: $(git rev-list --count HEAD 2>/dev/null || echo n/a)"
git log --oneline 2>/dev/null | head -10

echo "===== [2] SUSPICIOUS PATTERNS (base64/eval/obfuscation/download-exec) ====="
grep -rniE "base64\(|atob\(|btoa\(|fromCharCode|eval\(|shell_exec|Invoke-WebRequest|irm |iwr |curl .*\|" "${EXCL[@]}" "${EXT[@]}" . 2>/dev/null | grep -viE "test|example" | head -30

echo "===== [3] HARDCODED URLs (known-good filtered) ====="
grep -rnoE "https?://[a-zA-Z0-9\.\-]+" "${EXCL[@]}" "${EXT[@]}" . 2>/dev/null \
 | grep -vE "github\.com|w3\.org|tauri\.app|rust-lang|mozilla|docs\.rs|anthropic|npmjs|shadcn|vitejs|typescriptlang|apache\.org|gnu\.org|reactjs|crates\.io|wezterm|linux\.do|openai|googleapis|schema\.|json-schema|example\.com|localhost|127\.0\.0\.1|opencollective|raw\.githubusercontent|registry\.|licenses|wikipedia" | sort -u | head -40

echo "===== [4] IP ADDRESSES (loopback/private/CGNAT filtered) ====="
grep -rnoE "([0-9]{1,3}\.){3}[0-9]{1,3}" "${EXCL[@]}" "${EXT[@]}" . 2>/dev/null \
 | grep -vE "127\.0\.0\.1|0\.0\.0\.0|255\.255|192\.168|10\.[0-9]|172\.(1[6-9]|2[0-9]|3[01])\.|1\.1\.1\.1|8\.8\.8\.8|100\.(6[0-9]|7[0-9])\." | sort -u | head -20

echo "===== [5] TELEMETRY / ANALYTICS ====="
grep -rniE "telemetry|analytics|sentry|mixpanel|posthog|segment|amplitude|google-analytics" "${EXCL[@]}" "${EXT[@]}" . 2>/dev/null | grep -viE "test|example" | head -20

echo "===== [6] LONG BASE64 BLOBS (pubkey excluded) ====="
grep -rnE '"[A-Za-z0-9+/=]{200,}"' "${EXCL[@]}" "${EXT[@]}" . 2>/dev/null | grep -viE "pubkey|test|example" | head -10

echo "===== [7] HEX-ESCAPED STRINGS (obfuscation) ====="
grep -rnE '\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x' "${EXCL[@]}" -include="*.rs" -include="*.js" -include="*.ts" -include="*.tsx" . 2>/dev/null | grep -viE "test|example" | head -10

echo "===== [8] SUSPICIOUS CRATES (Cargo.lock) ====="
grep -E '^name = ' Cargo.lock 2>/dev/null | sort -u | grep -iE "telemetry|analytics|sentry|posthog|segment|exfil|reverse|rat|steal|sniffer|keylog" | head

echo "===== [9] BUILD/INSTALL HOOKS ====="
find . -path ./node_modules -prune -o -path ./target -prune -o -type f \( -name "*.nsh" -o -name "build.rs" -o -name "*hook*.cjs" -o -name "*hook*.js" \) -print 2>/dev/null | head -20

echo "===== DONE ====="
