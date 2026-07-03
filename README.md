# Complete Package

This repository contains everything needed to fully reconstruct the work from the self-improving system builder session. Nothing outside this repo is required.

## Contents

- `self-improving-system-builder/` — the complete, runnable, tested system
  (10 scripts, 4 test suites, IDKWIDK audit protocol files, Makefile).
- `skills/self-improving-system-builder.md` — reusable operating manual for
  building this class of system again from scratch, in a new context.
- `skills/idkwidk-audit-protocol.md` — reusable operating manual for the
  7-gate audit + action-plan loop, usable on any project.
- `IDEAS.md` — everything discussed, including out-of-scope items; no idea dies.

## Verify It Works

```bash
cd self-improving-system-builder
make test    # runs all 4 test suites
make lint    # syntax-checks every script
```

## Quick Start

```bash
git clone https://github.com/DXv-3/self-improving-system-builder
cd self-improving-system-builder/self-improving-system-builder
make test
source session-open.sh
```
