#!/usr/bin/env bash
set -euo pipefail
plan_json="${1:?plan path required}"
exec_json="${2:?execution result path required}"
plugin_data="${GROK_PLUGIN_DATA:-$HOME/.grok/operator-router}"
history="${plugin_data}/execution-history.ndjson"
mkdir -p "$plugin_data"
python3 -c "
import json, sys
from datetime import datetime
plan = json.load(open(sys.argv[1]))
exec_r = json.load(open(sys.argv[2]))
entry = {
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'task': plan.get('task', ''),
    'task_class': plan.get('task_class', 'unknown'),
    'execution_result': exec_r.get('execution_result', {})
}
with open(sys.argv[3], 'a') as f:
    f.write(json.dumps(entry) + chr(10))
print(json.dumps(entry))
" "$plan_json" "$exec_json" "$history"
