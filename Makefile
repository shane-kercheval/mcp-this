.PHONY: tests app build


####
# Project
####
build:
	uv sync

app:
	uv run python ./src/app.py my-command --a 1 --b 2

linting:
	uv run ruff check src
	uv run ruff check tests

unittests:
	uv run rm -f tests/test_files/log.log
	# pytest tests
	uv run coverage run -m pytest --durations=0 tests
	uv run coverage html

tests: linting unittests

open_coverage:
	open 'htmlcov/index.html'

# ####
# # DOCKER
# ####
# docker_build:
# 	docker compose -f docker-compose.yml build

# docker_run: docker_build
# 	docker compose -f docker-compose.yml up

# docker_down:
# 	docker compose down --remove-orphans

# docker_rebuild:
# 	docker compose -f docker-compose.yml build --no-cache

# docker_bash:
# 	docker compose -f docker-compose.yml up --build bash
