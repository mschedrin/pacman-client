#!/usr/bin/env bash
# opencode-review.sh - custom review script for ralphex external review phase.
#
# uses OpenCode CLI to perform code review with a configurable model,
# allowing a different model than the one used for task/review phases.
#
# config example (~/.config/ralphex/config or .ralphex/config):
#   external_review_tool = custom
#   custom_review_script = /path/to/opencode-review.sh
#
# environment variables:
OPENCODE_REVIEW_MODEL="${OPENCODE_REVIEW_MODEL:-githubcopilot/gpt-5.3-codex}"
OPENCODE_REVIEW_REASONING="${OPENCODE_REVIEW_REASONING:-high}"

set -euo pipefail

# verify opencode is available
command -v opencode >/dev/null 2>&1 || { echo "error: opencode is required but not found" >&2; exit 1; }

# verify jq is available (required for JSON config merging)
command -v jq >/dev/null 2>&1 || { echo "error: jq is required but not found" >&2; exit 1; }

# prompt file path is passed as the single argument
prompt_file="${1:-}"
if [[ -z "$prompt_file" || ! -f "$prompt_file" ]]; then
    echo "error: prompt file not provided or not found" >&2
    exit 1
fi

prompt=$(cat "$prompt_file")

# build config with permissions, model override for coder agent, and reasoning effort.
# reasoning effort is a passthrough option — opencode forwards it directly to the provider.
base_config=$(jq -nc \
    --arg model "$OPENCODE_REVIEW_MODEL" \
    --arg reasoning "$OPENCODE_REVIEW_REASONING" \
    '{
        permission: {"*": "allow"},
        agent: {
            coder: {
                model: $model,
                reasoningEffort: $reasoning
            }
        }
    }')

# merge with existing OPENCODE_CONFIG_CONTENT if set
if [[ -n "${OPENCODE_CONFIG_CONTENT:-}" ]]; then
    OPENCODE_CONFIG_CONTENT=$(echo "$OPENCODE_CONFIG_CONTENT" | jq -c --argjson base "$base_config" '. * $base')
else
    OPENCODE_CONFIG_CONTENT="$base_config"
fi
export OPENCODE_CONFIG_CONTENT

opencode run --model "$OPENCODE_REVIEW_MODEL" "$prompt"
