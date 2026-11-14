.PHONY: help validate compose-config nginx-test

help:
	@echo "make validate        static repository checks (Python 3 only)"
	@echo "make compose-config  validate compose.yaml with .env.example (needs Docker)"
	@echo "make nginx-test      nginx -t on the NGINX configurations (needs Docker)"

validate:
	python3 scripts/validate_repo.py

compose-config:
	docker compose --env-file .env.example -f compose.yaml config --quiet

nginx-test:
	bash scripts/check-nginx.sh
