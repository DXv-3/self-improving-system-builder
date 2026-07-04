#!/usr/bin/env bash
set -euo pipefail
task="${1:?task required}"
workspace="${2:-$PWD}"
mode="${3:-preview}"
plugin_data="${GROK_PLUGIN_DATA:-$HOME/.grok/operator-router}"
scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$plugin_data"
echo "$task" > "${plugin_data}/last-task.txt"
python3 "$scripts_dir/route-task.py" "$task" "$workspace"
plan_path="${plugin_data}/last-plan.json"
if [[ ! -f "$plan_path" ]]; then
  echo "ERROR: route-task.py did not produce a plan"
  exit 1
fi
if [[ "$mode" == "execute" ]]; then
  python3 "$scripts_dir/execute-plan-safe.py" "$plan_path" --allow-risky > "${plugin_data}/last-execution.json"
  bash "$scripts_dir/save-execution-result.sh" "$plan_path" "${plugin_data}/last-execution.json"
  python3 "$scripts_dir/rebuild-reliability.py"
  python3 "$scripts_dir/mine-recipes.py"
else
  echo "Preview mode. Plan saved to $plan_path"
fi
