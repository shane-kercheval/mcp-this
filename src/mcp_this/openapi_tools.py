"""OpenAPI tools integration for mcp-this using FastMCP."""

import os
import re
import json
from typing import Any, Protocol
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, model_validator
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType


class FastMCPTool(Protocol):
    """Protocol for FastMCP tool objects."""

    description: str
    inputSchema: dict[str, Any] | None  # noqa: N815

    async def run(self, parameters: dict[str, Any]) -> object:
        """Run the tool with given parameters."""
        ...


class AuthConfig(BaseModel):
    """Authentication configuration for OpenAPI endpoints."""

    type: str = Field(..., pattern="^(bearer|api_key|basic)$")
    token: str | None = None
    key_name: str | None = None
    key_value: str | None = None

    @model_validator(mode='after')
    def validate_auth_fields(self) -> 'AuthConfig':
        """Validate auth fields based on type."""
        if self.type == 'bearer' and not self.token:
            raise ValueError('Bearer auth requires token')
        if self.type == 'api_key' and not self.key_value:
            raise ValueError('API key auth requires key_value')
        return self


class RetryConfig(BaseModel):
    """Retry configuration for HTTP requests."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    timeout: int = Field(default=30, ge=1, le=300)


class OpenAPIConfig(BaseModel):
    """Configuration for an OpenAPI specification."""

    spec_url: str = Field(..., pattern=r"^(https?://|file://)")
    base_url: str | None = None
    auth: AuthConfig | None = None
    retry: RetryConfig = RetryConfig()
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []
    tool_prefix: str | None = None


class OpenAPIToolExtractor:
    """Extracts and configures tools from OpenAPI specifications."""

    def __init__(self):
        self.client_cache: dict[str, httpx.AsyncClient] = {}

    def resolve_auth_value(self, value: str) -> str:
        """Resolve environment variables in auth values."""
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            env_value = os.getenv(env_var)
            if env_value is None:
                raise ValueError(f"Environment variable {env_var} not found")
            return env_value
        return value

    def apply_authentication_to_client(
        self, client: httpx.AsyncClient, auth_config: AuthConfig,
    ) -> None:
        """Apply authentication configuration to HTTP client."""
        auth_type = auth_config.type

        if auth_type == 'bearer':
            token = self.resolve_auth_value(auth_config.token)
            client.headers['Authorization'] = f'Bearer {token}'
        elif auth_type == 'api_key':
            key_name = auth_config.key_name or 'X-API-Key'
            key_value = self.resolve_auth_value(auth_config.key_value)
            client.headers[key_name] = key_value
        elif auth_type == 'basic':
            # Basic auth implementation would go here
            pass

    def create_route_maps(self, config: OpenAPIConfig) -> list[RouteMap]:
        """Create route maps for include/exclude patterns."""
        route_maps = []

        # Exclude patterns first (order matters)
        for pattern in config.exclude_patterns:
            route_maps.append(RouteMap(
                methods="*",
                pattern=pattern,
                mcp_type=MCPType.EXCLUDE,
            ))

        # Include patterns
        for pattern in config.include_patterns:
            route_maps.append(RouteMap(
                methods="*",
                pattern=pattern,
                mcp_type=MCPType.TOOL,
            ))

        # Default: all endpoints become tools
        if not route_maps:
            route_maps.append(RouteMap(mcp_type=MCPType.TOOL))

        return route_maps

    async def fetch_openapi_spec(self, spec_url: str) -> dict[str, Any]:
        """Fetch OpenAPI specification from URL or file."""
        if spec_url.startswith('file://'):
            return await self._fetch_local_spec(spec_url)
        return await self._fetch_remote_spec(spec_url)

    async def _fetch_local_spec(self, spec_url: str) -> dict[str, Any]:
        """Fetch OpenAPI spec from local file."""
        import aiofiles

        file_path = spec_url[7:]  # Remove 'file://'
        if not Path(file_path).exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {file_path}")

        async with aiofiles.open(file_path, encoding='utf-8') as f:
            content = await f.read()

        if file_path.endswith('.json'):
            return json.loads(content)
        if file_path.endswith(('.yaml', '.yml')):
            import yaml
            return yaml.safe_load(content)

        # Try to parse as JSON first, then YAML
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import yaml
            return yaml.safe_load(content)

    async def _fetch_remote_spec(self, spec_url: str) -> dict[str, Any]:
        """Fetch OpenAPI spec from remote URL."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(spec_url)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                return response.json()
            if 'yaml' in content_type or 'yml' in content_type:
                import yaml
                return yaml.safe_load(response.text)
            # Try to parse as JSON first, then YAML
            try:
                return response.json()
            except json.JSONDecodeError:
                import yaml
                return yaml.safe_load(response.text)

    async def extract_tools_from_openapi(
        self, config_name: str, config: OpenAPIConfig,
    ) -> list[dict[str, Any]]:
        """Extract tools from OpenAPI specification using FastMCP."""
        try:
            # Fetch OpenAPI spec
            spec = await self.fetch_openapi_spec(config.spec_url)

            # Create authenticated HTTP client
            client = httpx.AsyncClient(
                timeout=config.retry.timeout,
                base_url=config.base_url,
            )

            # Apply authentication
            if config.auth:
                self.apply_authentication_to_client(client, config.auth)

            # Create route maps for filtering
            route_maps = self.create_route_maps(config)

            # Create FastMCP server
            fastmcp_server = FastMCP.from_openapi(
                openapi_spec=spec,
                client=client,
                name=f"{config_name}_server",
                route_maps=route_maps,
                timeout=config.retry.timeout,
            )

            # Extract tools from FastMCP server
            fastmcp_tools = await fastmcp_server.get_tools()

            # Convert to mcp-this format
            tools_info = []
            for tool_name, fastmcp_tool in fastmcp_tools.items():
                tool_info = self.convert_fastmcp_tool_to_mcp_this_format(
                    tool_name, fastmcp_tool, config_name, config,
                )
                tools_info.append(tool_info)

            # Cache the client for execution
            self.client_cache[config_name] = client

            return tools_info

        except Exception as e:
            raise RuntimeError(f"Failed to extract tools from OpenAPI spec '{config_name}': {e!s}")

    def convert_fastmcp_tool_to_mcp_this_format(
        self,
        tool_name: str,
        fastmcp_tool: "FastMCPTool",
        config_name: str,
        config: OpenAPIConfig,
    ) -> dict[str, Any]:
        """Convert FastMCP tool to mcp-this format."""
        # Apply tool prefix if configured
        if config.tool_prefix:
            display_name = f"{config.tool_prefix}__{tool_name}"
        else:
            display_name = f"{config_name}__{tool_name}"

        # Sanitize function name
        function_name = re.sub(r'[^a-zA-Z0-9_]', '_', display_name)

        return {
            'config_name': config_name,
            'tool_name': display_name,
            'function_name': function_name,
            'description': fastmcp_tool.description,
            'parameters': self.extract_parameters_from_fastmcp_tool(fastmcp_tool),
            'fastmcp_tool': fastmcp_tool,  # Store for execution
            'execution_type': 'fastmcp',   # Flag for registration
        }

    def extract_parameters_from_fastmcp_tool(self, fastmcp_tool: "FastMCPTool") -> dict[str, Any]:
        """Extract parameter schema from FastMCP tool."""
        if hasattr(fastmcp_tool, 'inputSchema') and fastmcp_tool.inputSchema:
            return fastmcp_tool.inputSchema
        return {}


class OpenAPIExecutor:
    """Executes FastMCP tools within mcp-this context."""

    async def execute_fastmcp_tool(
        self, tool_info: dict[str, Any], parameters: dict[str, Any],
    ) -> str:
        """Execute a FastMCP tool and return the result as a string."""
        fastmcp_tool = tool_info['fastmcp_tool']

        try:
            # FastMCP tools have run() method that handles everything
            result = await fastmcp_tool.run(parameters)

            # Convert FastMCP ToolResult to string (mcp-this format)
            if hasattr(result, 'content') and result.content:
                content_parts = []
                for content_block in result.content:
                    if hasattr(content_block, 'text') and content_block.text is not None:
                        content_parts.append(content_block.text)
                    elif hasattr(content_block, 'data'):
                        content_parts.append(str(content_block.data))
                return '\n'.join(content_parts)
            if hasattr(result, 'structured_content'):
                return json.dumps(result.structured_content, indent=2)
            return str(result)

        except Exception as e:
            return f"API Error: {e!s}"


def validate_openapi_configs(configs: dict[str, Any]) -> dict[str, OpenAPIConfig]:
    """Validate OpenAPI configurations using Pydantic models."""
    validated_configs = {}
    for name, config in configs.items():
        try:
            validated_configs[name] = OpenAPIConfig(**config)
        except Exception as e:
            raise ValueError(f"Invalid OpenAPI config '{name}': {e}")
    return validated_configs


async def parse_openapi_configs(openapi_configs: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse OpenAPI configurations and extract all tools."""
    # Validate configurations
    validated_configs = validate_openapi_configs(openapi_configs)

    # Extract tools from each configuration
    extractor = OpenAPIToolExtractor()
    all_tools_info = []

    for config_name, config in validated_configs.items():
        try:
            tools_info = await extractor.extract_tools_from_openapi(config_name, config)
            all_tools_info.extend(tools_info)
        except Exception as e:
            print(f"Error processing OpenAPI config '{config_name}': {e}")

    return all_tools_info


def generate_fastmcp_tool_function_code(tool_info: dict[str, Any]) -> str:
    """Generate function code for FastMCP tool execution."""
    function_name = tool_info['function_name']

    # Extract parameter information
    parameters = tool_info.get('parameters', {})
    properties = parameters.get('properties', {})
    required = parameters.get('required', [])

    # Build function signature - required parameters first, then optional
    required_params = []
    optional_params = []
    
    for param_name, param_info in properties.items():
        param_type = param_info.get('type', 'str')
        python_type = 'str'  # Default to string

        if param_type == 'integer':
            python_type = 'int'
        elif param_type == 'number':
            python_type = 'float'
        elif param_type == 'boolean':
            python_type = 'bool'
        elif param_type == 'array':
            python_type = 'list'
        elif param_type == 'object':
            python_type = 'dict'

        if param_name in required:
            required_params.append(f"{param_name}: {python_type}")
        else:
            optional_params.append(f"{param_name}: {python_type} = None")
    
    # Combine required first, then optional
    param_list = required_params + optional_params

    params_str = ', '.join(param_list)

    function_lines = [
        f"async def {function_name}({params_str}):",
        "    parameters = {}",
    ]

    # Add parameter assignments
    for param in properties:
        function_lines.append(f'    if {param} is not None: parameters["{param}"] = {param}')

    function_lines.append("    return await execute_fastmcp_tool(fastmcp_tool_info, parameters)")

    return '\n'.join(function_lines)



def register_openapi_tools(tools_info: list[dict[str, Any]]) -> None:
    """Register OpenAPI tools with the MCP server."""
    from mcp_this.mcp_server import mcp

    executor = OpenAPIExecutor()

    for tool_info in tools_info:
        if tool_info.get('execution_type') != 'fastmcp':
            continue

        try:
            # Generate function code (follow existing pattern)
            function_code = generate_fastmcp_tool_function_code(tool_info)

            # Create execution namespace
            tool_namespace = {
                'fastmcp_tool_info': tool_info,
                'execute_fastmcp_tool': executor.execute_fastmcp_tool,
            }

            # Execute the generated function code
            exec(function_code, tool_namespace)

            # Get the created function
            handler = tool_namespace[tool_info['function_name']]

            # Register with MCP (same pattern as CLI tools)
            mcp.tool(
                name=tool_info['tool_name'],
                description=tool_info['description'],
            )(handler)

        except Exception as e:
            print(f"Error registering OpenAPI tool {tool_info['tool_name']}: {e}")

