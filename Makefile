.PHONY: setup test doctor doctor-full models lock
setup:
	bash scripts/bootstrap.sh

test:
	bash scripts/test.sh

doctor:
	.venv/bin/python scripts/check_env.py --profile core --strict

doctor-full:
	.venv/bin/python scripts/check_env.py --profile full --strict

models:
	.venv/bin/python scripts/prefetch_models.py --all

lock:
	bash scripts/lock.sh
