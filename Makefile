.PHONY: install lint test cov run load

install:
	pip install -r requirements.txt

lint:
	ruff check .

test:
	pytest -q

# gate: falha se linhas/statements < 85% (ver pyproject) ou branches < 80%
cov:
	pytest --cov --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=html
	python scripts/check_branch_cov.py 80

run:
	uvicorn src.controllers.api:app --port 8000

load:
	locust -f perf/locustfile.py --headless -u 50 -r 50 -t 20s --host http://localhost:8000 --csv perf/results
