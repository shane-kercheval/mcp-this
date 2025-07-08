"""Comprehensive tests for OpenAPI integration covering HTTP requests, auth, and tool registration."""

import json
import os
import pytest
import respx
import httpx
from unittest.mock import Mock, AsyncMock, patch
from typing import Any

from mcp_this.openapi_tools import (
    OpenAPIToolExtractor,
    OpenAPIExecutor,
    OpenAPIConfig,
    AuthConfig,
    RetryConfig,
    register_openapi_tools,
    generate_fastmcp_tool_function_code,
)


class MockFastMCPTool:
    """Mock FastMCP tool for testing."""

    def __init__(self, name: str, description: str = "Test tool", parameters: dict | None = None):
        self.name = name
        self.description = description
        self.inputSchema = parameters or {}
        self.run_mock = AsyncMock()

    async def run(self, parameters: dict[str, Any]) -> object:
        """Mock run method."""
        return await self.run_mock(parameters)


class MockFastMCPServer:
    """Mock FastMCP server for testing."""

    def __init__(self, tools: dict[str, MockFastMCPTool] | None = None):
        self.tools = tools or {}
        self.get_tools_mock = AsyncMock(return_value=self.tools)

    async def get_tools(self) -> dict[str, MockFastMCPTool]:
        """Mock get_tools method."""
        return await self.get_tools_mock()


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI specification for testing."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/users/{id}": {
                "get": {
                    "summary": "Get user by ID",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
                    ],
                    "responses": {"200": {"description": "User details"}},
                },
            },
            "/users": {
                "post": {
                    "summary": "Create user",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                    "required": ["name", "email"],
                                },
                            },
                        },
                    },
                    "responses": {"201": {"description": "User created"}},
                },
            },
        },
    }


@pytest.fixture
def sample_config():
    """Sample OpenAPI configuration."""
    return {
        "spec_url": "https://api.example.com/openapi.json",
        "base_url": "https://api.example.com",
        "auth": {
            "type": "bearer",
            "token": "test-token",
        },
        "retry": {
            "max_attempts": 3,
            "timeout": 30,
        },
        "include_patterns": ["^/users"],
        "exclude_patterns": ["^/admin"],
    }


class TestOpenAPIEndToEnd:
    """Test complete HTTP request pipeline."""

    @respx.mock
    async def test_get_request_with_path_and_query_params(self, sample_openapi_spec):
        """Test GET request with path and query parameters."""
        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock the actual API request
        respx.get("https://api.example.com/users/123").mock(
            return_value=httpx.Response(200, json={"id": 123, "name": "John Doe"}),
        )

        # Mock FastMCP
        mock_tool = MockFastMCPTool("get_users_id", "Get user by ID", {
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        })
        mock_tool.run_mock.return_value = Mock(
            content=[Mock(text='{"id": 123, "name": "John Doe"}')],
        )

        mock_server = MockFastMCPServer({"get_users_id": mock_tool})

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
            )

            tools = await extractor.extract_tools_from_openapi("test_api", config)

            assert len(tools) == 1
            assert tools[0]['tool_name'] == "test_api__get_users_id"
            assert tools[0]['execution_type'] == 'fastmcp'

            # Verify the mock was called correctly
            mock_fastmcp.from_openapi.assert_called_once()
            call_args = mock_fastmcp.from_openapi.call_args
            assert call_args.kwargs['openapi_spec'] == sample_openapi_spec
            assert call_args.kwargs['name'] == "test_api_server"

    @respx.mock
    async def test_post_request_with_json_body(self, sample_openapi_spec):
        """Test POST request with JSON body."""
        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock FastMCP
        mock_tool = MockFastMCPTool("post_users", "Create user", {
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
            },
            "required": ["name", "email"],
        })
        mock_tool.run_mock.return_value = Mock(
            content=[Mock(text='{"id": 456, "name": "Jane Doe", "email": "jane@example.com"}')],
        )

        mock_server = MockFastMCPServer({"post_users": mock_tool})

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
            )

            tools = await extractor.extract_tools_from_openapi("test_api", config)

            # Test execution
            executor = OpenAPIExecutor()
            result = await executor.execute_fastmcp_tool(
                tools[0], {"name": "Jane Doe", "email": "jane@example.com"},
            )

            assert '{"id": 456, "name": "Jane Doe", "email": "jane@example.com"}' in result
            mock_tool.run_mock.assert_called_once_with({"name": "Jane Doe", "email": "jane@example.com"})

    @respx.mock
    async def test_put_request_with_path_params(self, sample_openapi_spec):
        """Test PUT request with path parameters."""
        # Add PUT endpoint to spec
        sample_openapi_spec["paths"]["/users/{id}"]["put"] = {
            "summary": "Update user",
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                },
            ],
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                            "required": ["name"],
                        },
                    },
                },
            },
            "responses": {"200": {"description": "User updated"}},
        }

        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock FastMCP - include both GET and PUT tools
        get_tool = MockFastMCPTool("get_users_id", "Get user by ID")
        put_tool = MockFastMCPTool("put_users_id", "Update user", {
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "required": ["id", "name"],
        })
        put_tool.run_mock.return_value = Mock(
            content=[Mock(text='{"id": 123, "name": "Updated Name"}')],
        )

        mock_server = MockFastMCPServer({"get_users_id": get_tool, "put_users_id": put_tool})

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
            )

            tools = await extractor.extract_tools_from_openapi("test_api", config)

            # Should have both GET and PUT tools
            assert len(tools) >= 2
            put_tool = next((t for t in tools if "put" in t['tool_name']), None)
            assert put_tool is not None
            assert put_tool['execution_type'] == 'fastmcp'

    @respx.mock
    async def test_delete_request(self, sample_openapi_spec):
        """Test DELETE request."""
        # Add DELETE endpoint to spec
        sample_openapi_spec["paths"]["/users/{id}"]["delete"] = {
            "summary": "Delete user",
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                },
            ],
            "responses": {"204": {"description": "User deleted"}},
        }

        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock FastMCP - include GET, POST, and DELETE tools
        get_tool = MockFastMCPTool("get_users_id", "Get user by ID")
        post_tool = MockFastMCPTool("post_users", "Create user")
        delete_tool = MockFastMCPTool("delete_users_id", "Delete user", {
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        })
        delete_tool.run_mock.return_value = Mock(
            content=[Mock(text='User deleted successfully')],
        )

        mock_server = MockFastMCPServer({
            "get_users_id": get_tool,
            "post_users": post_tool,
            "delete_users_id": delete_tool,
        })

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
            )

            tools = await extractor.extract_tools_from_openapi("test_api", config)

            # Should have GET, POST, and DELETE tools
            assert len(tools) >= 3
            delete_tool = next((t for t in tools if "delete" in t['tool_name']), None)
            assert delete_tool is not None
            assert delete_tool['execution_type'] == 'fastmcp'


class TestOpenAPIAuthentication:
    """Test authentication headers are applied correctly."""

    @respx.mock
    async def test_bearer_auth_header_applied(self, sample_openapi_spec):
        """Test that bearer auth header is applied to HTTP client."""
        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock FastMCP
        mock_tool = MockFastMCPTool("get_users_id", "Get user by ID")
        mock_server = MockFastMCPServer({"get_users_id": mock_tool})

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
                auth=AuthConfig(type="bearer", token="test-bearer-token"),
            )

            await extractor.extract_tools_from_openapi("test_api", config)

            # Verify that FastMCP was called with a client that has auth headers
            mock_fastmcp.from_openapi.assert_called_once()
            call_args = mock_fastmcp.from_openapi.call_args
            client = call_args.kwargs['client']

            assert 'Authorization' in client.headers
            assert client.headers['Authorization'] == 'Bearer test-bearer-token'

    @respx.mock
    async def test_api_key_header_applied(self, sample_openapi_spec):
        """Test that API key header is applied to HTTP client."""
        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock FastMCP
        mock_tool = MockFastMCPTool("get_users_id", "Get user by ID")
        mock_server = MockFastMCPServer({"get_users_id": mock_tool})

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
                auth=AuthConfig(type="api_key", key_name="X-API-Key", key_value="test-api-key"),
            )

            await extractor.extract_tools_from_openapi("test_api", config)

            # Verify that FastMCP was called with a client that has auth headers
            mock_fastmcp.from_openapi.assert_called_once()
            call_args = mock_fastmcp.from_openapi.call_args
            client = call_args.kwargs['client']

            assert 'X-API-Key' in client.headers
            assert client.headers['X-API-Key'] == 'test-api-key'

    @respx.mock
    async def test_environment_variable_resolution_in_auth(self, sample_openapi_spec):
        """Test that environment variables are resolved in auth configuration."""
        # Set environment variable
        os.environ['TEST_API_TOKEN'] = 'env-token-value'

        try:
            # Mock the OpenAPI spec fetch
            respx.get("https://api.example.com/openapi.json").mock(
                return_value=httpx.Response(200, json=sample_openapi_spec),
            )

            # Mock FastMCP
            mock_tool = MockFastMCPTool("get_users_id", "Get user by ID")
            mock_server = MockFastMCPServer({"get_users_id": mock_tool})

            with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
                mock_fastmcp.from_openapi.return_value = mock_server

                extractor = OpenAPIToolExtractor()
                config = OpenAPIConfig(
                    spec_url="https://api.example.com/openapi.json",
                    base_url="https://api.example.com",
                    auth=AuthConfig(type="bearer", token="${TEST_API_TOKEN}"),
                )

                await extractor.extract_tools_from_openapi("test_api", config)

                # Verify that FastMCP was called with a client that has resolved auth
                mock_fastmcp.from_openapi.assert_called_once()
                call_args = mock_fastmcp.from_openapi.call_args
                client = call_args.kwargs['client']

                assert 'Authorization' in client.headers
                assert client.headers['Authorization'] == 'Bearer env-token-value'
        finally:
            # Clean up environment variable
            if 'TEST_API_TOKEN' in os.environ:
                del os.environ['TEST_API_TOKEN']


class TestOpenAPIToolRegistration:
    """Test tool registration with MCP."""

    def test_tools_registered_with_mcp(self):
        """Test that tools are registered with MCP server."""
        # Mock MCP server
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Create sample tool info
        tool_info = {
            'tool_name': 'test_api__get_users',
            'function_name': 'test_api__get_users',
            'description': 'Get users',
            'parameters': {
                'properties': {'limit': {'type': 'integer'}},
                'required': [],
            },
            'fastmcp_tool': MockFastMCPTool('get_users'),
            'execution_type': 'fastmcp',
        }

        with patch('mcp_this.mcp_server.mcp', mock_mcp):
            register_openapi_tools([tool_info])

            # Verify MCP tool registration was called
            mock_mcp.tool.assert_called_once_with(
                name='test_api__get_users',
                description='Get users',
            )
            mock_tool_decorator.assert_called_once()

    def test_generated_function_is_callable(self):
        """Test that generated function is callable."""
        tool_info = {
            'function_name': 'test_function',
            'parameters': {
                'properties': {
                    'name': {'type': 'string'},
                    'age': {'type': 'integer'},
                },
                'required': ['name'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Verify the generated code is valid Python
        assert 'async def test_function(' in function_code
        assert 'name: str' in function_code
        assert 'age: int = None' in function_code
        assert 'parameters = {}' in function_code
        assert 'execute_fastmcp_tool(fastmcp_tool_info, parameters)' in function_code

        # Test that the code compiles without syntax errors
        compile(function_code, '<string>', 'exec')

    def test_tool_names_are_sanitized(self):
        """Test that tool names are sanitized for Python function names."""
        extractor = OpenAPIToolExtractor()

        # Test with special characters
        tool_info = extractor.convert_fastmcp_tool_to_mcp_this_format(
            'get-users/by-id',
            MockFastMCPTool('get-users/by-id', 'Get user by ID'),
            'test_api',
            OpenAPIConfig(spec_url='https://example.com/openapi.json'),
        )

        # Function name should be sanitized
        assert tool_info['function_name'] == 'test_api__get_users_by_id'
        assert tool_info['tool_name'] == 'test_api__get-users/by-id'


class TestFastMCPIntegration:
    """Test FastMCP integration points."""

    @respx.mock
    async def test_fastmcp_server_creation(self, sample_openapi_spec):
        """Test that FastMCP server is created correctly."""
        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock FastMCP
        mock_tool = MockFastMCPTool("get_users_id", "Get user by ID")
        mock_server = MockFastMCPServer({"get_users_id": mock_tool})

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
                retry=RetryConfig(timeout=45),
            )

            await extractor.extract_tools_from_openapi("test_api", config)

            # Verify FastMCP.from_openapi was called with correct parameters
            mock_fastmcp.from_openapi.assert_called_once()
            call_args = mock_fastmcp.from_openapi.call_args

            assert call_args.kwargs['openapi_spec'] == sample_openapi_spec
            assert call_args.kwargs['name'] == "test_api_server"
            assert call_args.kwargs['timeout'] == 45
            assert isinstance(call_args.kwargs['client'], httpx.AsyncClient)
            assert isinstance(call_args.kwargs['route_maps'], list)

    @respx.mock
    async def test_route_maps_passed_to_fastmcp(self, sample_openapi_spec):
        """Test that route maps are passed to FastMCP correctly."""
        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock FastMCP
        mock_tool = MockFastMCPTool("get_users_id", "Get user by ID")
        mock_server = MockFastMCPServer({"get_users_id": mock_tool})

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
                include_patterns=["^/users"],
                exclude_patterns=["^/admin"],
            )

            await extractor.extract_tools_from_openapi("test_api", config)

            # Verify route maps were passed
            mock_fastmcp.from_openapi.assert_called_once()
            call_args = mock_fastmcp.from_openapi.call_args
            route_maps = call_args.kwargs['route_maps']

            assert len(route_maps) == 2
            # Should have exclude pattern first, then include pattern
            assert route_maps[0].pattern == "^/admin"
            assert route_maps[1].pattern == "^/users"

    @respx.mock
    async def test_http_client_passed_to_fastmcp(self, sample_openapi_spec):
        """Test that HTTP client is passed to FastMCP correctly."""
        # Mock the OpenAPI spec fetch
        respx.get("https://api.example.com/openapi.json").mock(
            return_value=httpx.Response(200, json=sample_openapi_spec),
        )

        # Mock FastMCP
        mock_tool = MockFastMCPTool("get_users_id", "Get user by ID")
        mock_server = MockFastMCPServer({"get_users_id": mock_tool})

        with patch('mcp_this.openapi_tools.FastMCP') as mock_fastmcp:
            mock_fastmcp.from_openapi.return_value = mock_server

            extractor = OpenAPIToolExtractor()
            config = OpenAPIConfig(
                spec_url="https://api.example.com/openapi.json",
                base_url="https://api.example.com",
                retry=RetryConfig(timeout=60),
            )

            await extractor.extract_tools_from_openapi("test_api", config)

            # Verify HTTP client was passed with correct configuration
            mock_fastmcp.from_openapi.assert_called_once()
            call_args = mock_fastmcp.from_openapi.call_args
            client = call_args.kwargs['client']

            assert isinstance(client, httpx.AsyncClient)
            assert client.base_url == "https://api.example.com"
            assert str(client.timeout) == "Timeout(timeout=60)"


class TestFunctionGeneration:
    """Test dynamic function generation."""

    def test_function_signature_generation(self):
        """Test that function signatures are generated correctly."""
        tool_info = {
            'function_name': 'test_function',
            'parameters': {
                'properties': {
                    'name': {'type': 'string'},
                    'age': {'type': 'integer'},
                    'active': {'type': 'boolean'},
                    'tags': {'type': 'array'},
                    'metadata': {'type': 'object'},
                },
                'required': ['name', 'age'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Check that all parameter types are correctly mapped
        assert 'name: str' in function_code
        assert 'age: int' in function_code
        assert 'active: bool = None' in function_code
        assert 'tags: list = None' in function_code
        assert 'metadata: dict = None' in function_code

    def test_generated_function_syntax_valid(self):
        """Test that generated function has valid Python syntax."""
        tool_info = {
            'function_name': 'valid_function_name',
            'parameters': {
                'properties': {
                    'param1': {'type': 'string'},
                    'param2': {'type': 'integer'},
                },
                'required': ['param1'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Should compile without syntax errors
        compile(function_code, '<string>', 'exec')

        # Should have proper async function structure
        assert function_code.strip().startswith('async def valid_function_name(')
        assert 'parameters = {}' in function_code
        assert 'return await execute_fastmcp_tool(fastmcp_tool_info, parameters)' in function_code

    def test_parameter_mapping_in_generated_function(self):
        """Test that parameters are correctly mapped in generated function."""
        tool_info = {
            'function_name': 'test_mapping',
            'parameters': {
                'properties': {
                    'required_param': {'type': 'string'},
                    'optional_param': {'type': 'integer'},
                },
                'required': ['required_param'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Check parameter handling
        assert 'required_param: str' in function_code
        assert 'optional_param: int = None' in function_code
        assert 'if required_param is not None: parameters["required_param"] = required_param' in function_code
        assert 'if optional_param is not None: parameters["optional_param"] = optional_param' in function_code


class TestParameterTypes:
    """Test different OpenAPI parameter types and scenarios."""

    def test_all_basic_types(self):
        """Test all basic OpenAPI types are handled correctly."""
        tool_info = {
            'function_name': 'test_all_types',
            'parameters': {
                'properties': {
                    'string_param': {'type': 'string'},
                    'integer_param': {'type': 'integer'},
                    'number_param': {'type': 'number'},
                    'boolean_param': {'type': 'boolean'},
                    'array_param': {'type': 'array'},
                    'object_param': {'type': 'object'},
                },
                'required': ['string_param', 'integer_param'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Check all type mappings
        assert 'string_param: str' in function_code
        assert 'integer_param: int' in function_code
        assert 'number_param: float = None' in function_code
        assert 'boolean_param: bool = None' in function_code
        assert 'array_param: list = None' in function_code
        assert 'object_param: dict = None' in function_code

    def test_path_parameters(self):
        """Test path parameters (required by nature)."""
        tool_info = {
            'function_name': 'get_user_by_id',
            'parameters': {
                'properties': {
                    'user_id': {'type': 'integer', 'in': 'path'},
                    'format': {'type': 'string', 'in': 'query'},
                },
                'required': ['user_id'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Path parameters should be required
        assert 'user_id: int' in function_code
        assert 'format: str = None' in function_code

    def test_query_parameters_with_defaults(self):
        """Test query parameters with default values."""
        tool_info = {
            'function_name': 'search_users',
            'parameters': {
                'properties': {
                    'q': {'type': 'string'},
                    'limit': {'type': 'integer', 'default': 10},
                    'offset': {'type': 'integer', 'default': 0},
                    'include_inactive': {'type': 'boolean', 'default': False},
                },
                'required': ['q'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Check that optional parameters get default None in function signature
        assert 'q: str' in function_code
        assert 'limit: int = None' in function_code
        assert 'offset: int = None' in function_code
        assert 'include_inactive: bool = None' in function_code

    def test_complex_array_parameters(self):
        """Test array parameters with item type specifications."""
        tool_info = {
            'function_name': 'bulk_update',
            'parameters': {
                'properties': {
                    'user_ids': {
                        'type': 'array',
                        'items': {'type': 'integer'}
                    },
                    'tags': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                },
                'required': ['user_ids'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Arrays should map to list type regardless of item type
        assert 'user_ids: list' in function_code
        assert 'tags: list = None' in function_code

    def test_nested_object_parameters(self):
        """Test object parameters with nested properties."""
        tool_info = {
            'function_name': 'create_user',
            'parameters': {
                'properties': {
                    'user_data': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'email': {'type': 'string'},
                            'profile': {
                                'type': 'object',
                                'properties': {
                                    'bio': {'type': 'string'},
                                    'age': {'type': 'integer'},
                                }
                            }
                        }
                    },
                },
                'required': ['user_data'],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Nested objects should map to dict type
        assert 'user_data: dict' in function_code

    def test_unknown_parameter_types(self):
        """Test handling of unknown or custom parameter types."""
        tool_info = {
            'function_name': 'test_unknown_types',
            'parameters': {
                'properties': {
                    'custom_type': {'type': 'custom'},
                    'unknown_type': {'type': 'unknown'},
                    'missing_type': {},  # No type specified
                },
                'required': [],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Unknown types should default to str
        assert 'custom_type: str = None' in function_code
        assert 'unknown_type: str = None' in function_code
        assert 'missing_type: str = None' in function_code

    def test_parameter_naming_edge_cases(self):
        """Test parameter names that need sanitization."""
        tool_info = {
            'function_name': 'test_param_names',
            'parameters': {
                'properties': {
                    'normal-param': {'type': 'string'},
                    'param.with.dots': {'type': 'integer'},
                    'param with spaces': {'type': 'boolean'},
                    'param@special!chars': {'type': 'array'},
                    'param/slash': {'type': 'object'},
                },
                'required': [],
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Check that parameter names are used as-is in the assignment (not sanitized)
        # since they're used as dictionary keys
        assert 'parameters["normal-param"]' in function_code
        assert 'parameters["param.with.dots"]' in function_code
        assert 'parameters["param with spaces"]' in function_code
        assert 'parameters["param@special!chars"]' in function_code
        assert 'parameters["param/slash"]' in function_code

    async def test_parameter_execution_with_different_types(self):
        """Test that parameters of different types are passed correctly during execution."""
        # Mock FastMCP tool
        mock_tool = MockFastMCPTool("test_types_tool")
        mock_tool.run_mock.return_value = Mock(
            content=[Mock(text='{"status": "success"}')]
        )

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_types_tool',
        }

        executor = OpenAPIExecutor()
        
        # Test with different parameter types
        test_params = {
            'string_val': 'hello',
            'int_val': 42,
            'float_val': 3.14,
            'bool_val': True,
            'list_val': [1, 2, 3],
            'dict_val': {'key': 'value'},
        }
        
        result = await executor.execute_fastmcp_tool(tool_info, test_params)

        # Verify the tool was called with the exact parameters
        mock_tool.run_mock.assert_called_once_with(test_params)
        assert '{"status": "success"}' in result

    def test_large_parameter_set(self):
        """Test handling of endpoints with many parameters."""
        properties = {}
        required = []
        
        # Create 20 parameters of various types
        for i in range(20):
            param_name = f'param_{i}'
            param_type = ['string', 'integer', 'boolean', 'array', 'object'][i % 5]
            properties[param_name] = {'type': param_type}
            
            # Make every 3rd parameter required
            if i % 3 == 0:
                required.append(param_name)

        tool_info = {
            'function_name': 'test_many_params',
            'parameters': {
                'properties': properties,
                'required': required,
            },
        }

        function_code = generate_fastmcp_tool_function_code(tool_info)

        # Check that all parameters are included
        for i in range(20):
            param_name = f'param_{i}'
            assert param_name in function_code
        
        # Check that some required parameters don't have defaults
        assert 'param_0: str' in function_code  # Required
        assert 'param_1: int = None' in function_code  # Optional
        assert 'param_3: list' in function_code  # Required
        assert 'param_4: dict = None' in function_code  # Optional

        # Verify the function compiles
        compile(function_code, '<string>', 'exec')


class TestResponseFormats:
    """Test different API response formats."""

    async def test_json_response_handling(self):
        """Test JSON response handling."""
        # Mock FastMCP tool with JSON response
        mock_tool = MockFastMCPTool("test_tool")
        mock_tool.run_mock.return_value = Mock(
            content=[Mock(text='{"status": "success", "data": {"id": 123}}')],
        )

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        executor = OpenAPIExecutor()
        result = await executor.execute_fastmcp_tool(tool_info, {})

        assert '{"status": "success", "data": {"id": 123}}' in result
        mock_tool.run_mock.assert_called_once_with({})

    async def test_structured_content_response(self):
        """Test structured content response handling."""
        # Mock FastMCP tool with structured content
        mock_tool = MockFastMCPTool("test_tool")
        mock_tool.run_mock.return_value = Mock(
            content=None,
            structured_content={"users": [{"id": 1, "name": "John"}]},
        )

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        executor = OpenAPIExecutor()
        result = await executor.execute_fastmcp_tool(tool_info, {})

        # Should be JSON formatted
        assert '"users"' in result
        assert '"id": 1' in result
        assert '"name": "John"' in result

    async def test_binary_response_handling(self):
        """Test binary response handling."""
        # Mock FastMCP tool with binary data
        mock_tool = MockFastMCPTool("test_tool")
        mock_content = Mock()
        mock_content.text = None
        mock_content.data = "binary data content"
        mock_tool.run_mock.return_value = Mock(
            content=[mock_content],
        )

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        executor = OpenAPIExecutor()
        result = await executor.execute_fastmcp_tool(tool_info, {})

        assert 'binary data content' in result


class TestErrorScenarios:
    """Test error handling."""

    async def test_api_404_error_handling(self):
        """Test API 404 error handling."""
        # Mock FastMCP tool that raises an error
        mock_tool = MockFastMCPTool("test_tool")
        mock_tool.run_mock.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=Mock(status_code=404),
        )

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        executor = OpenAPIExecutor()
        result = await executor.execute_fastmcp_tool(tool_info, {})

        assert result.startswith("API Error:")
        assert "404" in result or "Not Found" in result

    async def test_api_500_error_handling(self):
        """Test API 500 error handling."""
        # Mock FastMCP tool that raises a server error
        mock_tool = MockFastMCPTool("test_tool")
        mock_tool.run_mock.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=Mock(), response=Mock(status_code=500),
        )

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        executor = OpenAPIExecutor()
        result = await executor.execute_fastmcp_tool(tool_info, {})

        assert result.startswith("API Error:")
        assert "500" in result or "Internal Server Error" in result

    async def test_network_timeout_handling(self):
        """Test network timeout handling."""
        # Mock FastMCP tool that raises a timeout
        mock_tool = MockFastMCPTool("test_tool")
        mock_tool.run_mock.side_effect = httpx.TimeoutException("Request timeout")

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        executor = OpenAPIExecutor()
        result = await executor.execute_fastmcp_tool(tool_info, {})

        assert result.startswith("API Error:")
        assert "timeout" in result.lower()

    async def test_invalid_json_response_handling(self):
        """Test invalid JSON response handling."""
        # Mock FastMCP tool with invalid response
        mock_tool = MockFastMCPTool("test_tool")
        mock_tool.run_mock.return_value = Mock(
            content=[Mock(text='invalid json {')],
        )

        tool_info = {
            'fastmcp_tool': mock_tool,
            'tool_name': 'test_tool',
        }

        executor = OpenAPIExecutor()
        result = await executor.execute_fastmcp_tool(tool_info, {})

        # Should handle gracefully and return the content as-is
        assert 'invalid json {' in result


class TestEdgeCases:
    """Test edge cases and configuration scenarios."""

    async def test_yaml_spec_fetching(self):
        """Test YAML spec fetching."""
        yaml_spec = """
        openapi: 3.0.0
        info:
          title: Test API
          version: 1.0.0
        paths:
          /test:
            get:
              summary: Test endpoint
              responses:
                '200':
                  description: OK
        """

        with respx.mock:
            respx.get("https://api.example.com/openapi.yaml").mock(
                return_value=httpx.Response(
                    200,
                    content=yaml_spec,
                    headers={"content-type": "application/yaml"},
                ),
            )

            extractor = OpenAPIToolExtractor()
            spec = await extractor.fetch_openapi_spec("https://api.example.com/openapi.yaml")

            assert spec['openapi'] == '3.0.0'
            assert spec['info']['title'] == 'Test API'
            assert '/test' in spec['paths']

    async def test_local_file_spec_fetching(self, tmp_path):
        """Test local file spec fetching."""
        # Create a temporary OpenAPI spec file
        spec_content = {
            "openapi": "3.0.0",
            "info": {"title": "Local API", "version": "1.0.0"},
            "paths": {"/local": {"get": {"summary": "Local endpoint", "responses": {"200": {"description": "OK"}}}}},
        }

        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(spec_content))

        extractor = OpenAPIToolExtractor()
        spec = await extractor.fetch_openapi_spec(f"file://{spec_file}")

        assert spec['openapi'] == '3.0.0'
        assert spec['info']['title'] == 'Local API'
        assert '/local' in spec['paths']

    def test_tool_name_collision_handling(self):
        """Test tool name collision handling."""
        extractor = OpenAPIToolExtractor()

        # Create tools with same name from different configs
        tool1 = extractor.convert_fastmcp_tool_to_mcp_this_format(
            'get_users',
            MockFastMCPTool('get_users', 'Get users from API 1'),
            'api1',
            OpenAPIConfig(spec_url='https://api1.com/openapi.json'),
        )

        tool2 = extractor.convert_fastmcp_tool_to_mcp_this_format(
            'get_users',
            MockFastMCPTool('get_users', 'Get users from API 2'),
            'api2',
            OpenAPIConfig(spec_url='https://api2.com/openapi.json'),
        )

        # Should have different tool names due to config prefix
        assert tool1['tool_name'] == 'api1__get_users'
        assert tool2['tool_name'] == 'api2__get_users'
        assert tool1['function_name'] == 'api1__get_users'
        assert tool2['function_name'] == 'api2__get_users'

    async def test_missing_environment_variables(self):
        """Test missing environment variables handling."""
        extractor = OpenAPIToolExtractor()

        # Test with non-existent environment variable
        with pytest.raises(ValueError, match="Environment variable NON_EXISTENT_VAR not found"):
            extractor.resolve_auth_value("${NON_EXISTENT_VAR}")

        # Test with normal value (should pass through)
        result = extractor.resolve_auth_value("normal-value")
        assert result == "normal-value"

