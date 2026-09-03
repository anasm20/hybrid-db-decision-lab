PYTHON ?= python3

.PHONY: up down logs validate analyze cost site new-exp

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

validate:
	$(PYTHON) scripts/validate_repo.py

analyze:
	$(PYTHON) analysis/analyze.py

cost:
	$(PYTHON) analysis/cost_model.py

site: analyze cost
	$(PYTHON) -m http.server 8000 -d site

new-exp:
	$(PYTHON) scripts/new_experiment.py --scenario primary-failure --repetitions 10
