SHELL := /bin/bash
SKILL_DIR := $(shell cd "$(dir $(MAKEFILE_LIST))" && pwd)
SCRIPTS := $(SKILL_DIR)/scripts
TESTS := $(SKILL_DIR)/tests
N ?= 50
.PHONY: test test-smoke test-conflict test-skill-direct test-property lint help audit-status audit-done audit-reset
help:
	@echo "make test               - Run all 4 test suites"
	@echo "make test-property N=50 - Property-based tests (N iterations)"
	@echo "make lint               - Syntax check all scripts"
	@echo "make audit-status       - Show IDKWIDK action plan"
test: test-conflict test-smoke test-skill-direct test-property
	@echo "All tests passed."
test-smoke:
	@python3 $(TESTS)/test_smoke.py
test-conflict:
	@python3 $(TESTS)/test_conflict_detection.py
test-skill-direct:
	@python3 $(TESTS)/test_skill_direct.py
test-property:
	@python3 $(TESTS)/test_property_based.py $(N)
lint:
	@for f in $(SCRIPTS)/*.py $(SKILL_DIR)/*.py; do python3 -m py_compile "$$f" && echo "  OK: $$f" || exit 1; done
	@for f in $(SCRIPTS)/*.sh $(SKILL_DIR)/*.sh; do bash -n "$$f" && echo "  OK: $$f" || exit 1; done
	@echo "All syntax checks passed."
audit-status:
	@python3 $(SKILL_DIR)/idkwidk-action-plan.py --status
audit-done:
	@test -n "$(ID)" || (echo 'Usage: make audit-done ID=3'; exit 1)
	@python3 $(SKILL_DIR)/idkwidk-action-plan.py --done $(ID)
audit-reset:
	@python3 $(SKILL_DIR)/idkwidk-action-plan.py --reset
