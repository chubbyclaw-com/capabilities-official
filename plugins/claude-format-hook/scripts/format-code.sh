#!/bin/bash

# Claude Code Auto-Formatting Hook
# Automatically formats source code files after Claude edits them.
#
# Strategy:
#   1. Honor project orchestrator (treefmt / dprint) if configured.
#   2. Otherwise pick a formatter by extension, preferring whichever
#      tool the project configures (biome vs prettier, ruff, etc.).
#   3. Skip common vendored / generated paths.
#   4. Never block Claude: always exit 0. When a formatter fails we emit
#      a PostToolUse additionalContext JSON on stdout so Claude sees the
#      failure and can react; otherwise output is empty.
#
# Originally adapted from https://github.com/ryanlewis/claude-format-hook (MIT).

json_input=$(cat)

if command -v jq &> /dev/null; then
    file_path=$(printf '%s' "$json_input" | jq -r '.tool_input.file_path // empty')
else
    file_path=$(printf '%s' "$json_input" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
fi

if [ -z "$file_path" ] || [ ! -f "$file_path" ]; then
    exit 0
fi

case "$file_path" in
    /*) ;;
    *) file_path="$PWD/$file_path" ;;
esac

case "$file_path" in
    */node_modules/*|*/vendor/*|*/dist/*|*/build/*|*/out/*|\
    */.venv/*|*/venv/*|*/__pycache__/*|*/target/*|\
    */.next/*|*/.nuxt/*|*/.turbo/*|*/.cache/*|*/coverage/*)
        exit 0
        ;;
esac

file_dir=$(dirname "$file_path")
basename="${file_path##*/}"
extension="${basename##*.}"
[ "$extension" = "$basename" ] && extension=""
extension=$(printf '%s' "$extension" | tr '[:upper:]' '[:lower:]')

# Error accumulator. Reporting requires jq (to build valid JSON).
# Without jq we silently degrade.
errors=""
err_file=""
if command -v jq &> /dev/null; then
    err_file=$(mktemp 2>/dev/null)
    [ -n "$err_file" ] && trap 'rm -f "$err_file"' EXIT
fi

# Runs a formatter. Captures stderr and the exit code; on failure, appends
# a diagnostic line to the errors accumulator. Always returns 0.
run_fmt() {
    local tool="$1"
    shift
    if [ -z "$err_file" ]; then
        "$@" > /dev/null 2>&1
        return 0
    fi
    : > "$err_file"
    "$@" > /dev/null 2>"$err_file"
    local rc=$?
    if [ $rc -eq 0 ]; then
        return 0
    fi
    local err_content
    err_content=$(< "$err_file")
    if [ -n "$err_content" ]; then
        errors+=$'\n'"[$tool] (exit $rc) $err_content"
    else
        errors+=$'\n'"[$tool] exited with $rc (no stderr output)"
    fi
    return 0
}

find_up() {
    local dir="$1"
    shift
    while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "." ]; do
        local name
        for name in "$@"; do
            if [ -e "$dir/$name" ]; then
                printf '%s/%s\n' "$dir" "$name"
                return 0
            fi
        done
        local parent
        parent=$(dirname "$dir")
        [ "$parent" = "$dir" ] && break
        dir="$parent"
    done
    return 1
}

emit_and_exit() {
    if [ -n "$errors" ] && [ -n "$err_file" ]; then
        local msg="claude-format-hook: formatter(s) reported issues while processing ${file_path}:${errors}"
        jq -nc --arg ctx "$msg" \
            '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}'
    fi
    exit 0
}

has_biome_config() {
    find_up "$file_dir" biome.json biome.jsonc &> /dev/null
}

has_prettier_config() {
    find_up "$file_dir" \
        .prettierrc .prettierrc.json .prettierrc.yaml .prettierrc.yml \
        .prettierrc.js .prettierrc.cjs .prettierrc.mjs .prettierrc.toml \
        prettier.config.js prettier.config.cjs prettier.config.mjs &> /dev/null
}

# ----- Phase 1: project-level orchestrators -----

if command -v treefmt &> /dev/null && find_up "$file_dir" treefmt.toml .treefmt.toml &> /dev/null; then
    run_fmt treefmt treefmt "$file_path"
    emit_and_exit
fi

if command -v dprint &> /dev/null && find_up "$file_dir" dprint.json dprint.jsonc .dprint.json &> /dev/null; then
    run_fmt dprint dprint fmt "$file_path"
    emit_and_exit
fi

# ----- Phase 2: per-extension, project-preference aware -----

format_js_like() {
    if has_biome_config && command -v biome &> /dev/null; then
        run_fmt biome biome check --write --no-errors-on-unmatched "$file_path"
    elif has_prettier_config && command -v prettier &> /dev/null; then
        run_fmt prettier prettier --write --log-level=error "$file_path"
    elif command -v biome &> /dev/null; then
        run_fmt biome biome check --write --no-errors-on-unmatched "$file_path"
    elif command -v prettier &> /dev/null; then
        run_fmt prettier prettier --write --log-level=error "$file_path"
    fi
}

format_with_prettier() {
    if command -v prettier &> /dev/null; then
        run_fmt prettier prettier --write --log-level=error "$file_path"
    fi
}

case "$extension" in
    js|jsx|ts|tsx|mjs|cjs|mts|cts|json|jsonc)
        format_js_like
        ;;

    py)
        # Import-sort prelude is allowed to fail silently — the error, if any,
        # will resurface in the subsequent `ruff format` call.
        if command -v ruff &> /dev/null; then
            ruff check --select I --fix "$file_path" > /dev/null 2>&1 || true
            run_fmt ruff ruff format "$file_path"
        elif command -v uv &> /dev/null; then
            uv tool run ruff check --select I --fix "$file_path" > /dev/null 2>&1 || true
            run_fmt ruff uv tool run ruff format "$file_path"
        fi
        ;;

    md|mdx|yaml|yml|css|scss|less|html|htm|vue|svelte|graphql|gql)
        format_with_prettier
        ;;

    toml)
        if command -v taplo &> /dev/null; then
            run_fmt taplo taplo format "$file_path"
        fi
        ;;

    sh|bash|zsh)
        if command -v shfmt &> /dev/null; then
            run_fmt shfmt shfmt -w "$file_path"
        fi
        ;;

    go)
        if command -v goimports &> /dev/null; then
            run_fmt goimports goimports -w "$file_path"
        elif command -v gofmt &> /dev/null; then
            run_fmt gofmt gofmt -w "$file_path"
        fi
        ;;

    rs)
        if command -v rustfmt &> /dev/null; then
            run_fmt rustfmt rustfmt --edition 2021 "$file_path"
        fi
        ;;

    kt|kts)
        if command -v ktlint &> /dev/null; then
            run_fmt ktlint ktlint --format "$file_path"
        elif command -v ktfmt &> /dev/null; then
            run_fmt ktfmt ktfmt "$file_path"
        fi
        ;;

    "")
        if head -c 128 "$file_path" 2>/dev/null | head -n1 | grep -qE '^#!.*\b(ba|z)?sh\b'; then
            if command -v shfmt &> /dev/null; then
                run_fmt shfmt shfmt -w "$file_path"
            fi
        fi
        ;;
esac

emit_and_exit
