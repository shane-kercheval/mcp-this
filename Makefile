.PHONY: tests build linting unittests coverage mcp_dev mcp_install mcp_test verify package package-build package-publish help

-include .env
export

####
# Project
####

help: ## Display this help
	@echo "MCP-This Development Commands"
	@echo "============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Install dependencies 
	uv sync

####
# Development
####

mcp_dev: ## Run the MCP server with default config in development mode
	MCP_THIS_CONFIG_PATH=./src/mcp_this/configs/default.yaml uv run mcp dev ./src/mcp_this/mcp_server.py

mcp_custom: ## Run the MCP server with a custom config (path in CONFIG var)
	MCP_THIS_CONFIG_PATH=$(CONFIG) uv run mcp dev ./src/mcp_this/mcp_server.py

mcp_install: ## Install the MCP server in Claude Desktop with the default config
	uv run mcp install --name "MCP-This" ./src/mcp_this/mcp_server.py

mcp_install_custom: ## Install the MCP server with a custom config (path in CONFIG var)
	uv run mcp install --name "MCP-This" ./src/mcp_this/mcp_server.py -- --config $(CONFIG)

mcp_test: ## Run the sample test server
	uv run mcp dev ./src/mcp_this/test_server.py


mcp_inspector_github:
	npx @modelcontextprotocol/inspector \
		uv run -m mcp_this \
		--config_path /Users/shanekercheval/repos/mcp-this/src/mcp_this/configs/github.yaml

####
# Testing
####

linting: ## Run linting checks
	uv run ruff check src --fix --unsafe-fixes
	uv run ruff check tests --fix --unsafe-fixes

unittests: ## Run unit tests
	uv run pytest tests -v --durations=10

tests: linting coverage

coverage: ## Run tests with coverage
	uv run coverage run -m pytest --durations=0 tests
	uv run coverage html

open_coverage: ## Open coverage report in browser
	open 'htmlcov/index.html'

verify: linting unittests coverage ## Run all verification checks

chat:
	uv run python examples/cli.py \
		-chat \
		--mcp_config examples/mcp_config_cli.json \
		--model 'gpt-4o'

chat_tools:
	uv run python examples/cli.py \
		-tools \
		--mcp_config examples/mcp_config_cli.json

####
# Packaging and Distribution
####

package-build: ## Build the package
	rm -rf dist/*
	uv build --no-sources

package-publish: ## Publish the package to PyPI (requires UV_PUBLISH_TOKEN)
	uv publish --token ${UV_PUBLISH_TOKEN}

package: package-build package-publish ## Build and publish the package

####
# Development Tools
####

add-dep: ## Add a dependency (PKG=package_name)
	uv add $(PKG)

add-dev-dep: ## Add a development dependency (PKG=package_name)
	uv add $(PKG) --group dev

## Run MCP-This with uvx directly (for Claude Desktop testing)
test-uvx: 
	npx -y uvx mcp-this --config ./src/mcp_this/configs/default.yaml --verbose
