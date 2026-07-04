#!/usr/bin/env bash
set -euo pipefail
plugin_data="${GROK_PLUGIN_DATA:-$HOME/.grok/operator-router}"
registry="${plugin_data}/registry.json"
scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$plugin_data"
python3 -c "import json; json.dump({'skills': [], 'commands': [], 'instruction_files': []}, open('$registry', 'w'), indent=2)"
for source in grok claude agents; do
  case $source in
    grok) dir="$HOME/.grok/skills" ;;
    claude) dir="$HOME/.claude/skills" ;;
    agents) dir="$HOME/.agents/skills" ;;
  esac
  if [[ -d "$dir" ]]; then
    for skill_dir in "$dir"/*/; do
      [[ -d "$skill_dir" ]] && python3 "$scripts_dir/import-existing-skill.py" "$skill_dir" "$registry" 2>/dev/null || true
    done
  fi
done
python3 "$scripts_dir/render-registry-summary.py" "$registry"
