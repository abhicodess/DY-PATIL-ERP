.PHONY: test test-unit test-integration test-coverage test-load lint security-scan clean

test:
	pytest

test-unit:
	pytest tests/unit

test-integration:
	pytest tests/integration

test-coverage:
	pytest --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-load:
	locust -f tests/load/test_load.py --headless --users 100 --spawn-rate 10 -t 1m

lint:
	flake8 . --exclude=venv,migrations
	black . --check --exclude=venv,migrations

security-scan:
	bandit -r . -ll --exclude=./tests,./venv,./migrations

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -f .coverage
