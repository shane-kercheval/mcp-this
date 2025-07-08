"""Test OpenAPI integration functionality."""

import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from mcp_this.openapi_tools import (
    OpenAPIConfig,
    AuthConfig,
    RetryConfig,
    OpenAPIToolExtractor,
    OpenAPIExecutor,
    validate_openapi_configs,
    parse_openapi_configs,
)


class TestOpenAPIConfig:
    """Test OpenAPI configuration validation."""

    def test_valid_config(self):
        """Test valid OpenAPI configuration."""
        config = OpenAPIConfig(
            spec_url="https://api.example.com/openapi.json",
            base_url="https://api.example.com",
            auth=AuthConfig(type="bearer", token="test-token"),
            retry=RetryConfig(max_attempts=3, timeout=30),
            include_patterns=["^/users", "^/posts"],
            exclude_patterns=["^/admin"],
            tool_prefix="example",
        )

        assert config.spec_url == "https://api.example.com/openapi.json"
        assert config.base_url == "https://api.example.com"
        assert config.auth.type == "bearer"
        assert config.auth.token == "test-token"
        assert config.retry.max_attempts == 3
        assert config.retry.timeout == 30
        assert config.include_patterns == ["^/users", "^/posts"]
        assert config.exclude_patterns == ["^/admin"]
        assert config.tool_prefix == "example"

    def test_invalid_spec_url(self):
        """Test invalid spec URL."""
        with pytest.raises(ValueError, match="spec_url"):
            OpenAPIConfig(spec_url="invalid-url")

    def test_bearer_auth_validation(self):
        """Test bearer auth validation."""
        with pytest.raises(ValueError, match="Bearer auth requires token"):
            OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                auth=AuthConfig(type="bearer"),
            )

    def test_api_key_auth_validation(self):
        """Test API key auth validation."""
        with pytest.raises(ValueError, match="API key auth requires key_value"):
            OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                auth=AuthConfig(type="api_key", key_name="X-API-Key"),
            )


class TestOpenAPIToolExtractor:
    """Test OpenAPI tool extraction."""

    def test_resolve_auth_value_env_var(self):
        """Test resolving environment variable in auth value."""
        extractor = OpenAPIToolExtractor()

        # Test with environment variable
        os.environ["TEST_TOKEN"] = "secret-token"
        try:
            result = extractor.resolve_auth_value("${TEST_TOKEN}")
            assert result == "secret-token"
        finally:
            del os.environ["TEST_TOKEN"]

    def test_resolve_auth_value_literal(self):
        """Test resolving literal auth value."""
        extractor = OpenAPIToolExtractor()

        result = extractor.resolve_auth_value("literal-token")
        assert result == "literal-token"

    def test_resolve_auth_value_missing_env_var(self):
        """Test resolving missing environment variable."""
        extractor = OpenAPIToolExtractor()

        with pytest.raises(ValueError, match="Environment variable MISSING_VAR not found"):
            extractor.resolve_auth_value("${MISSING_VAR}")

    def test_create_route_maps(self):
        """Test route map creation."""
        extractor = OpenAPIToolExtractor()
        config = OpenAPIConfig(
            spec_url="https://api.example.com/openapi.json",
            include_patterns=["^/users", "^/posts"],
            exclude_patterns=["^/admin", "^/internal"],
        )

        route_maps = extractor.create_route_maps(config)

        # Should have 4 route maps: 2 excludes + 2 includes
        assert len(route_maps) == 4

        # Check exclude patterns come first
        assert route_maps[0].pattern == "^/admin"
        assert route_maps[1].pattern == "^/internal"

        # Check include patterns
        assert route_maps[2].pattern == "^/users"
        assert route_maps[3].pattern == "^/posts"

    def test_create_route_maps_default(self):
        """Test default route map creation."""
        extractor = OpenAPIToolExtractor()
        config = OpenAPIConfig(spec_url="https://api.example.com/openapi.json")

        route_maps = extractor.create_route_maps(config)

        # Should have 1 default route map
        assert len(route_maps) == 1

    @patch('httpx.AsyncClient')
    async def test_fetch_openapi_spec_remote_json(self, mock_client: MagicMock) -> None:
        """Test fetching OpenAPI spec from remote JSON URL."""
        extractor = OpenAPIToolExtractor()

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"openapi": "3.0.0", "info": {"title": "Test API"}}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status.return_value = None

        mock_client_instance = Mock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await extractor.fetch_openapi_spec("https://api.example.com/openapi.json")

        assert result == {"openapi": "3.0.0", "info": {"title": "Test API"}}

    async def test_fetch_openapi_spec_file(self, tmp_path: Path) -> None:
        """Test fetching OpenAPI spec from local file."""
        extractor = OpenAPIToolExtractor()

        # Create a test JSON file
        test_spec = {"openapi": "3.0.0", "info": {"title": "Test API"}}
        test_file = tmp_path / "test-spec.json"
        test_file.write_text('{"openapi": "3.0.0", "info": {"title": "Test API"}}')

        result = await extractor.fetch_openapi_spec(f"file://{test_file}")

        assert result == test_spec

    async def test_fetch_openapi_spec_file_not_found(self):
        """Test fetching OpenAPI spec from non-existent file."""
        extractor = OpenAPIToolExtractor()

        with pytest.raises(FileNotFoundError, match="OpenAPI spec file not found"):
            await extractor.fetch_openapi_spec("file:///nonexistent/spec.json")

    def test_convert_fastmcp_tool_to_mcp_this_format(self):
        """Test converting FastMCP tool to mcp-this format."""
        extractor = OpenAPIToolExtractor()

        # Create mock FastMCP tool
        mock_tool = Mock()
        mock_tool.description = "Test tool description"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}},
            "required": ["param1"],
        }

        config = OpenAPIConfig(
            spec_url="https://api.example.com/openapi.json",
            tool_prefix="test_api",
        )

        result = extractor.convert_fastmcp_tool_to_mcp_this_format(
            "get_users", mock_tool, "example", config,
        )

        assert result['config_name'] == "example"
        assert result['tool_name'] == "test_api__get_users"
        assert result['function_name'] == "test_api__get_users"
        assert result['description'] == "Test tool description"
        assert result['execution_type'] == "fastmcp"
        assert result['fastmcp_tool'] == mock_tool


class TestOpenAPIExecutor:
    """Test OpenAPI tool execution."""

    @pytest.mark.asyncio
    async def test_execute_fastmcp_tool_success(self):
        """Test successful FastMCP tool execution."""
        executor = OpenAPIExecutor()

        # Mock result with content
        mock_content_block = Mock()
        mock_content_block.text = "API response data"

        mock_result = Mock()
        mock_result.content = [mock_content_block]

        # Mock tool
        mock_tool = Mock()
        mock_tool.run = AsyncMock(return_value=mock_result)

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        parameters = {"param1": "value1"}

        result = await executor.execute_fastmcp_tool(tool_info, parameters)

        assert result == "API response data"
        mock_tool.run.assert_called_once_with(parameters)

    @pytest.mark.asyncio
    async def test_execute_fastmcp_tool_error(self):
        """Test FastMCP tool execution error handling."""
        executor = OpenAPIExecutor()

        # Mock tool that raises exception
        mock_tool = Mock()
        mock_tool.run = AsyncMock(side_effect=Exception("API error"))

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        parameters = {"param1": "value1"}

        result = await executor.execute_fastmcp_tool(tool_info, parameters)

        assert result == "API Error: API error"


class TestValidateOpenAPIConfigs:
    """Test OpenAPI configuration validation."""

    def test_validate_valid_configs(self):
        """Test validating valid configurations."""
        configs = {
            "api1": {
                "spec_url": "https://api.example.com/openapi.json",
                "auth": {
                    "type": "bearer",
                    "token": "test-token",
                },
            },
            "api2": {
                "spec_url": "https://api2.example.com/openapi.json",
            },
        }

        result = validate_openapi_configs(configs)

        assert len(result) == 2
        assert isinstance(result["api1"], OpenAPIConfig)
        assert isinstance(result["api2"], OpenAPIConfig)

    def test_validate_invalid_configs(self):
        """Test validating invalid configurations."""
        configs = {
            "api1": {
                "spec_url": "invalid-url",  # Invalid URL
            },
        }

        with pytest.raises(ValueError, match="Invalid OpenAPI config 'api1'"):
            validate_openapi_configs(configs)


@pytest.mark.asyncio
class TestParseOpenAPIConfigs:
    """Test parsing OpenAPI configurations."""

    @patch('mcp_this.openapi_tools.OpenAPIToolExtractor.extract_tools_from_openapi')
    async def test_parse_configs_success(self, mock_extract: MagicMock) -> None:
        """Test successful parsing of OpenAPI configs."""
        mock_extract.return_value = [
            {
                'tool_name': 'api1__get_users',
                'description': 'Get users',
                'execution_type': 'fastmcp',
            },
        ]

        configs = {
            "api1": {
                "spec_url": "https://api.example.com/openapi.json",
            },
        }

        result = await parse_openapi_configs(configs)

        assert len(result) == 1
        assert result[0]['tool_name'] == 'api1__get_users'
        mock_extract.assert_called_once()

    @patch('mcp_this.openapi_tools.OpenAPIToolExtractor.extract_tools_from_openapi')
    async def test_parse_configs_error_handling(self, mock_extract: MagicMock) -> None:
        """Test error handling in parsing OpenAPI configs."""
        mock_extract.side_effect = Exception("Failed to extract tools")

        configs = {
            "api1": {
                "spec_url": "https://api.example.com/openapi.json",
            },
        }

        # Should not raise exception, but return empty list
        result = await parse_openapi_configs(configs)

        assert result == []

