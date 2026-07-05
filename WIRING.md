# System Wiring Guide

How the three core repos connect into a closed-loop self-improving system.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        THE TRIAD                                    │
│                                                                     │
│  ┌─────────────────┐   brain_client.py   ┌──────────────────────┐  │
│  │   the-brain     │◄────────────────────│ self-improving-       │  │
│  │                 │                     │ system-builder        │  │
│  │  brain.db (WAL) │                     │                       │  │
│  │  MCP WebSocket  │────────────────────►│  trigger_dispatcher   │  │
│  │  JSONL sync     │  skill mutations    │  improve_skill        │  │
│  │  vector search  │                     │  SkillMutationAuditor │  │
│  └────────┬────────┘                     └──────────┬───────────┘  │
│           │                                         │               │
│           │ events / queries                        │ model calls   │
│           ▼                                         ▼               │
│  ┌────────────────┐                     ┌──────────────────────┐   │
│  │ conductor-     │                     │  model_caller.py      │   │
│  │ protocol-v2    │                     │                       │   │
│  │                │                     │  Z.AI (GLM)  priority │   │
│  │  operator-     │                     │  Anthropic   fallback │   │
│  │  router        │                     │  OpenAI      fallback │   │
│  │  bundle-       │                     │  Ollama      local    │   │
│  │  forensics     │                     └──────────────────────┘   │
│  └────────────────┘                                                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  zai-wrap / build-watch  (http://127.0.0.1:8790)            │   │
│  │  .build-watch/events.jsonl ◄── _emit_build_watch_event()    │   │
│  │  Live dashboard shows every improve_skill() cycle in real-  │   │
│  │  time: plan → model call → gate audit → applied/rejected    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flows

### Improvement Cycle (every N seconds via `--watch`)

1. `trigger_dispatcher.py` polls `learning_memory.jsonl` for skills with recent failures
2. For each candidate: calls `improve_skill(skill_name)`
3. `improve_skill` loads skill definition via `brain_client → the-brain MCP`
4. Loads failure context from `learning_memory.jsonl`
5. Calls `model_caller.py` → Z.AI GLM (or fallback chain)
6. `SkillMutationAuditor` runs all 7 IDKWIDK gates
7. On pass: patch pushed to `the-brain` + written to `skills/` on disk
8. `_emit_build_watch_event()` → `.build-watch/events.jsonl`
9. `zai-wrap build-watch` dashboard renders the event live
10. Outcome appended to `learning_memory.jsonl`

### Brain ↔ Self-Improver Sync

- `brain_client.py` connects to `the-brain` via 5-path resolver
- All skill mutations stored in `brain.db` as `type=skill_mutation` records
- `the-brain` vector search can recall past mutations for context in future cycles
- WAL mode ensures no lock contention between concurrent readers

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `ZAI_API_KEY` | — | Z.AI/GLM primary provider |
| `ZAI_MODEL` | `glm-4-plus` | GLM model name override |
| `ANTHROPIC_API_KEY` | — | Anthropic fallback |
| `ANTHROPIC_MODEL` | `claude-3-5-haiku-20241022` | Haiku for cost efficiency |
| `OPENAI_API_KEY` | — | OpenAI second fallback |
| `OPENAI_MODEL` | `gpt-4o-mini` | Mini for cost efficiency |
| `OLLAMA_HOST` | `http://localhost:11434` | Local Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Local model |
| `BUILD_WATCH_DIR` | `.build-watch` in cwd | Where events.jsonl lives |
| `BRAIN_PATH` | Auto-resolved | Path to `the-brain` clone |

## Quick Start — Full Closed Loop

```bash
# 1. Set at least one provider key
export ZAI_API_KEY="your-key-here"
# or: export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Cold-start the triad
bash the-brain/bootstrap.sh

# 3. Start the build-watch dashboard (zai-wrap)
cd zai-wrap && build-watch on
# Dashboard: http://127.0.0.1:8790

# 4. Dry-run a single skill improvement
cd self-improving-system-builder
python3 improve_skill.py --skill context_spinner --dry-run --json

# 5. Start the live loop (60-second interval)
python3 trigger_dispatcher.py --watch --interval 60

# 6. Run all tests
pytest tests/ -v
```

## Adding a New Skill

```bash
# Create a minimal skill definition
cat > skills/my_skill.json << 'EOF'
{
  "name": "my_skill",
  "steps": ["step 1", "step 2"],
  "constraints": ["must be idempotent"],
  "notes": "does X when Y happens"
}
EOF

# Run one improvement cycle
python3 improve_skill.py --skill my_skill --dry-run
```

## Gap Status (post this commit)

| ID | Gap | Status |
|---|---|---|
| `IGNITION-01` | No bootstrap command | ✅ `bootstrap.sh` |
| `IGNITION-02` | `trigger_dispatcher` missing | ✅ committed |
| `MEMORY-01` | JSONL/brain divergence | ✅ `sync_local_jsonl_to_brain()` |
| `PROOF-01` | No closed-loop tests | ✅ `tests/test_closed_loop.py` |
| `INTERFACE-01` | BrainSync not contract-tested | ✅ `TestBrainSyncAPIContract` |
| `CALIB-01` | No success metrics | ✅ `metrics.py` |
| `DEP-02` | SQLite WAL not enforced | ✅ `_get_conn()` |
| `RECOV-01` | No backup | ✅ `backup.sh` + plist |
| **`IMPROVE-01`** | **`improve_skill()` was a TODO** | ✅ **`improve_skill.py`** |
| **`MODEL-01`** | **No model caller** | ✅ **`model_caller.py`** |
| **`AUDIT-01`** | **No mutation gating** | ✅ **`SkillMutationAuditor`** |
| **`VIZ-01`** | **No build-watch integration** | ✅ **`_emit_build_watch_event()`** |
| `DEP-01` | No pinned requirements | ⏳ Next |
| `SEC-01` | No MCP WebSocket auth | ⏳ Next |
| `INTERFACE-02` | No harmony event schema | ⏳ Week 2 |
| `PROOF-02` | No conductor boundary test | ⏳ Week 2 |
| `OPTIONALITY-02` | `MODEL_FALLBACK_CHAIN` hardcoded | ✅ now in env vars |
| `SEC-02` | No HMAC on harmony socket | ⏳ Week 2 |
| `SCALE-01` | No TTL/archival on brain.db | ⏳ Week 2 |
