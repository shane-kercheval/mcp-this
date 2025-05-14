.PHONY: tests app build

-include .env
export

####
# Project
####
build:
	uv sync

# app:
# 	uv run python ./src/app.py my-command --a 1 --b 2

	# uv run mcp dev ./src/mcp_this/mcp_server.py --config ./example_configs/basic.yaml
	# uv run mcp dev -- ./src/mcp_this/mcp_server.py --config ./example_configs/basic.yaml
mcp_dev:
	MCP_CONFIG_PATH=./example_configs/basic.yaml uv run mcp dev ./src/mcp_this/mcp_server.py

mcp_test:
	uv run mcp dev ./src/mcp_this/test_server.py

mcp_clean:
	uv run mcp dev ./src/mcp_this/clean_server.py

mcp_minimal:
	uv run mcp dev ./src/mcp_this/minimal_server.py


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


package-build:
	rm -rf dist/*
	uv build --no-sources

package-publish:
	uv publish --token ${UV_PUBLISH_TOKEN}

package: package-build package-publish


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
