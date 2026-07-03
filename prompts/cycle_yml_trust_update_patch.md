# cycle.yml — trust_update patch (Priority 11)

Add the following step to `.github/workflows/cycle.yml` after the `generate_human_report` step:

```yaml
- name: Apply trust updates if enough samples
  run: |
    SAMPLE_COUNT=$(python3 -c "
import json
from pathlib import Path
lines = Path('learning_memory.jsonl').read_text().splitlines() if Path('learning_memory.jsonl').exists() else []
from collections import Counter
cats = Counter(json.loads(l).get('category','unknown') for l in lines if l.strip())
print(min(cats.values()) if cats else 0)
")
    if [ "$SAMPLE_COUNT" -ge 5 ]; then
      python3 scripts/trust_update.py --apply
    else
      echo "Trust update skipped: only $SAMPLE_COUNT min samples per category (need 5)"
    fi
  continue-on-error: true
```

This closes the learning loop: once you have 5+ real operator cycles per category, trust weights update automatically on every run.
