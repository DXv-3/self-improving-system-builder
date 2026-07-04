#!/usr/bin/env bash
IDKWIDK_ROOT=""
dir="$PWD"
while [[ "$dir" != "/" ]]; do
  for f in "$dir/IDKWIDK.md" "$dir/IDKWIDK-single.md"; do
    if [[ -f "$f" ]]; then
      IDKWIDK_ROOT="$f"
      break 2
    fi
  done
  dir="$(dirname "$dir")"
done
if [[ -n "$IDKWIDK_ROOT" ]]; then
  export IDKWIDK_ACTIVE=1
  export IDKWIDK_FILE="$IDKWIDK_ROOT"
  echo "IDKWIDK protocol ACTIVE"
  echo "  Protocol file: $IDKWIDK_ROOT"
  echo "  The 7-gate audit will run before any task is declared complete."
else
  echo "IDKWIDK protocol not found."
fi
return 0 2>/dev/null || true
