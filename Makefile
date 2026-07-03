install:
	pip install pytest

test:
	python3 -m pytest tests/ -v

test-fast:
	python3 tests/test_forward_executor.py
	python3 tests/test_integrations.py
	python3 tests/test_proof_and_cycle.py
	python3 tests/test_meta_cycle.py
	python3 tests/test_adaptive_meta_cycle.py

run-bundle-forensics:
	python3 scripts/run_adaptive_meta_cycle.py examples/bundle_forensics_case

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
