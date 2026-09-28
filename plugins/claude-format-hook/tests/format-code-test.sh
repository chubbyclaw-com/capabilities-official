#!/bin/bash

set -euo pipefail

plugin_root=$(cd "$(dirname "$0")/.." && pwd)
hook="$plugin_root/scripts/format-code.sh"
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT

fake_bin="$test_root/bin"
project="$test_root/project"
format_log="$test_root/formatted-files"
mkdir -p "$fake_bin" "$project"

cat > "$fake_bin/goimports" <<'EOF'
#!/bin/bash
printf '%s\n' "${@: -1}" >> "$FORMAT_LOG"
EOF
chmod +x "$fake_bin/goimports"

export FORMAT_LOG="$format_log"
export PATH="$fake_bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

assert_formatted() {
    local expected="$1"
    if ! grep -Fxq "$expected" "$format_log"; then
        printf 'expected formatter to receive %s\n' "$expected" >&2
        printf 'actual formatter calls:\n' >&2
        cat "$format_log" >&2 2>/dev/null || true
        exit 1
    fi
}

assert_not_formatted() {
    local unexpected="$1"
    if grep -Fxq "$unexpected" "$format_log"; then
        printf 'expected formatter to skip %s\n' "$unexpected" >&2
        exit 1
    fi
}

# Regression: removing Claude's file_path handling would stop existing installs
# from formatting files after Edit/Write.
printf 'package sample\n' > "$project/claude.go"
(
    cd "$project"
    printf '%s' '{"tool_input":{"file_path":"claude.go"}}' | "$hook"
)
assert_formatted "$project/claude.go"

: > "$format_log"
printf 'package sample\n' > "$project/first.go"
printf 'package sample\n' > "$project/file with spaces.go"

# Regression: Codex sends the whole apply_patch payload in tool_input.command,
# so looking only for file_path silently formats nothing.
codex_input=$(jq -nc --arg command '*** Begin Patch
*** Update File: first.go
@@
-package old
+package sample
*** Add File: file with spaces.go
+package sample
*** Delete File: removed.go
*** End Patch' '{tool_name:"apply_patch",tool_input:{command:$command}}')
(
    cd "$project"
    printf '%s' "$codex_input" | "$hook"
)

assert_formatted "$project/first.go"
assert_formatted "$project/file with spaces.go"
assert_not_formatted "$project/removed.go"

printf 'format-code hook tests passed\n'
