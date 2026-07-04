SHELL := /bin/bash
SKILL_DIR := $(shell cd "$(dirname "$(MAKEFILE_LIST)")" && pwd)
SCRIPTS := $(SKILL_DIR)/scripts
TESTS := $(SKILL_DIR)/tests
.PHONY: test test-smoke test-conflict test-skill-direct test-property lint install help audit-status audit-done audit-reset
help:
	@echo "Available targets:"
	@echo "  test               - Run all tests"
	@echo "  test-property N=200 - Property-based tests"
	@echo "  lint               - Syntax check all scripts"
	@echo "  audit-status       - Show IDKWIDK action plan"
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
	@for f in $(SCRIPTS)/*.py; do python3 -m py_compile "$$f" && echo "  OK: $$f" || exit 1; done
	@for f in $(SCRIPTS)/*.sh $(SKILL_DIR)/*.sh; do bash -n "$$f" && echo "  OK: $$f" || exit 1; done
	@python3 -m py_compile $(SKILL_DIR)/idkwidk-action-plan.py && echo "  OK: idkwidk-action-plan.py"
	@python3 -m py_compile $(SKILL_DIR)/track-audit.py && echo "  OK: track-audit.py"
	@python3 -m py_compile $(SKILL_DIR)/test-idkwidk.py && echo "  OK: test-idkwidk.py"
	@echo "All syntax checks passed."
audit-status:
	@python3 $(SKILL_DIR)/idkwidk-action-plan.py --status
audit-done:
	@test -n "$(ID)" || (echo 'ID required: make audit-done ID=3' && exit 1)
	@python3 $(SKILL_DIR)/idkwidk-action-plan.py --done $(ID)
audit-reset:
	@python3 $(SKILL_DIR)/idkwidk-action-plan.py --reset
