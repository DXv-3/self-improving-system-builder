#!/bin/bash
# setup_brain_sync.sh — Wire self-improving-system-builder to the-brain
#
# Run once after cloning both repos to the same parent directory:
#   bash setup_brain_sync.sh
#
# What this does:
#   1. Verifies the-brain and brain_sync.py are present
#   2. Initializes brain.db if it doesn't exist
#   3. Backfills existing learning_memory.jsonl into brain.db
#   4. Prints MCP server config for Claude Desktop

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BRAIN_ROOT="$(cd "$REPO_ROOT/../the-brain" 2>/dev/null && pwd)" || BRAIN_ROOT=""

echo "=== brain_sync setup ==="
echo "self-improving-system-builder: $REPO_ROOT"
echo "the-brain:                     ${BRAIN_ROOT:-NOT FOUND}"
echo ""

# Check the-brain exists
if [ -z "$BRAIN_ROOT" ] || [ ! -f "$BRAIN_ROOT/brain_sync.py" ]; then
  echo "ERROR: the-brain repo not found at ../the-brain/"
  echo "Clone it with:"
  echo "  git clone git@github.com:DXv-3/the-brain.git ../the-brain"
  echo "Or set: export BRAIN_REPO_PATH=/path/to/the-brain"
  exit 1
fi

echo "[OK] the-brain found at: $BRAIN_ROOT"

# Initialize brain.db if not present
BRAIN_DB="$BRAIN_ROOT/brain.db"
if [ ! -f "$BRAIN_DB" ]; then
  echo "Initializing brain.db..."
  sqlite3 "$BRAIN_DB" < "$BRAIN_ROOT/brain_schema.sql"
  echo "[OK] brain.db created"
else
  echo "[OK] brain.db exists at: $BRAIN_DB"
fi

# Seed KG (run ingest.py)
echo "Seeding knowledge graph..."
cd "$BRAIN_ROOT" && python ingest.py
cd "$REPO_ROOT"

# Backfill existing learning_memory.jsonl
if [ -f "$REPO_ROOT/learning_memory.jsonl" ]; then
  echo "Backfilling learning_memory.jsonl into brain.db..."
  BRAIN_REPO_PATH="$BRAIN_ROOT" python "$REPO_ROOT/brain_push.py" --flush
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To add the-brain as an MCP server in Claude Desktop,"
echo "add this to your claude_desktop_config.json:"
echo ""
cat <<EOF
{
  \"mcpServers\": {
    \"the-brain\": {
      \"command\": \"python\",
      \"args\": [\"$BRAIN_ROOT/mcp_server.py\"],
      \"env\": {
        \"BRAIN_DB_PATH\": \"$BRAIN_DB\"
      }
    }
  }
}
EOF
echo ""
echo "Then restart Claude Desktop and look for 'the-brain' in your MCP tools."
