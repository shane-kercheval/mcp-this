# 🚀 OpenAPI Integration Implementation Plan for mcp-this

**Target**: Implement OpenAPI specification support for mcp-this using FastMCP as the underlying engine.

**Approach**: Leverage FastMCP's proven OpenAPI parsing and execution capabilities while maintaining mcp-this architecture and configuration patterns.

## 📋 Implementation Overview

This implementation uses FastMCP (`fastmcp>=2.2.0`) to handle OpenAPI parsing, HTTP requests, authentication, and error handling. We extract tool information from FastMCP servers and integrate them into mcp-this using the existing tool registration patterns.

## 🎯 Phase 1: Dependencies and Core Structure

### 1.1 Update Dependencies

**File**: `pyproject.toml`
```toml
dependencies = [
    # ... existing dependencies
    "fastmcp>=2.2.0",
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
]
```

### 1.2 Create Core OpenAPI Module

**File**: `src/mcp_this/openapi_tools.py`

**Key Imports** (Critical - these are verified to exist):
```python
import asyncio
import os
import re
from typing import Dict, List, Any, Optional
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType
```

**Core Classes to Implement**:

1. `OpenAPIToolExtractor` - Extracts tool info from FastMCP servers
2. `OpenAPIExecutor` - Executes FastMCP tools within mcp-this context  
3. `OpenAPIConfigValidator` - Validates configuration using Pydantic

## 🔧 Phase 2: OpenAPI Tool Extraction (Critical Implementation)

### 2.1 Tool Extractor Implementation

**Class**: `OpenAPIToolExtractor`

**Critical Method**: `extract_tools_from_openapi()`

This method must:
1. Fetch OpenAPI spec from URL or file
2. Create authenticated httpx.AsyncClient
3. Use `FastMCP.from_openapi()` to create a server
4. Extract tools from the FastMCP server using `await fastmcp_server.get_tools()`
5. Convert FastMCP tools to mcp-this format

**Key FastMCP Integration Pattern**:
```python
# This is the proven pattern from FastMCP tests
fastmcp_server = FastMCP.from_openapi(
    openapi_spec=spec,
    client=client,
    name=f"{config_name}_server", 
    route_maps=route_maps,
    timeout=timeout_value,
)

# Extract tools - this is how FastMCP exposes them
fastmcp_tools = await fastmcp_server.get_tools()
```

### 2.2 Authentication Handling

**Critical**: Apply authentication to the httpx.AsyncClient **before** passing to FastMCP:

```python
def apply_authentication_to_client(self, client: httpx.AsyncClient, auth_config: dict):
    auth_type = auth_config.get('type')
    
    if auth_type == 'bearer':
        token = self.resolve_auth_value(auth_config['token'])
        client.headers['Authorization'] = f'Bearer {token}'
    elif auth_type == 'api_key':
        key_name = auth_config.get('key_name', 'X-API-Key') 
        key_value = self.resolve_auth_value(auth_config['key_value'])
        client.headers[key_name] = key_value
```

### 2.3 Route Filtering with RouteMap

**Use FastMCP's RouteMap system** for include/exclude patterns:

```python
def create_route_maps(self, config: dict) -> List[RouteMap]:
    route_maps = []
    
    # Exclude patterns first (order matters)
    for pattern in config.get('exclude_patterns', []):
        route_maps.append(RouteMap(
            methods="*",
            pattern=pattern, 
            mcp_type=MCPType.EXCLUDE
        ))
    
    # Include patterns
    for pattern in config.get('include_patterns', []):
        route_maps.append(RouteMap(
            methods="*",
            pattern=pattern,
            mcp_type=MCPType.TOOL
        ))
    
    # Default: all endpoints become tools
    if not route_maps:
        route_maps.append(RouteMap(mcp_type=MCPType.TOOL))
    
    return route_maps
```

## ⚡ Phase 3: Tool Execution Bridge (Critical)

### 3.1 FastMCP Tool Executor

**Class**: `OpenAPIExecutor`

**Critical Method**: `execute_fastmcp_tool()`

This bridges FastMCP tool execution with mcp-this:

```python
async def execute_fastmcp_tool(self, tool_info: dict, parameters: dict) -> str:
    fastmcp_tool = tool_info['fastmcp_tool']
    
    try:
        # FastMCP tools have run() method that handles everything
        result = await fastmcp_tool.run(parameters)
        
        # Convert FastMCP ToolResult to string (mcp-this format)
        if hasattr(result, 'content') and result.content:
            content_parts = []
            for content_block in result.content:
                if hasattr(content_block, 'text'):
                    content_parts.append(content_block.text)
                elif hasattr(content_block, 'data'):
                    content_parts.append(str(content_block.data))
            return '\n'.join(content_parts)
        elif hasattr(result, 'structured_content'):
            import json
            return json.dumps(result.structured_content, indent=2)
        else:
            return str(result)
            
    except Exception as e:
        return f"API Error: {str(e)}"
```

### 3.2 Tool Info Conversion

**Critical**: Convert FastMCP tools to mcp-this format:

```python
def convert_fastmcp_tool_to_mcp_this_format(
    self, tool_name: str, fastmcp_tool, config_name: str, config: dict
) -> Dict[str, Any]:
    
    return {
        'config_name': config_name,
        'tool_name': tool_name,
        'function_name': tool_name.replace('-', '_'), 
        'description': fastmcp_tool.description,
        'parameters': self.extract_parameters_from_fastmcp_tool(fastmcp_tool),
        'fastmcp_tool': fastmcp_tool,  # Store for execution
        'execution_type': 'fastmcp',   # Flag for registration
    }
```

## 🔗 Phase 4: Integration with mcp-this

### 4.1 Update Main Server Registration

**File**: `src/mcp_this/mcp_server.py`

**Make `register_all()` async**:
```python
async def register_all(config: dict) -> None:
    """Register CLI tools, prompts, and OpenAPI tools from configuration."""
    
    # Existing registrations
    if 'tools' in config:
        register_tools(config)
    if 'prompts' in config:
        prompts_info = parse_prompts(config)
        register_prompts(prompts_info)
    
    # NEW: Register OpenAPI tools
    if 'openapi' in config:
        from mcp_this.openapi_tools import parse_openapi_configs, register_openapi_tools
        api_tools_info = await parse_openapi_configs(config['openapi'])
        register_openapi_tools(api_tools_info)
```

**Update `init_server()` to handle async**:
```python
def init_server(config_path: str | None = None, tools: str | None = None) -> None:
    config = load_config(config_path, tools)
    validate_config(config)
    
    # Handle async registration
    import asyncio
    asyncio.run(register_all(config))
```

### 4.2 Tool Registration Function

**File**: `src/mcp_this/openapi_tools.py`

**Function**: `register_openapi_tools()`

```python
def register_openapi_tools(tools_info: List[Dict[str, Any]]) -> None:
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
```

## ✅ Phase 5: Configuration Validation

### 5.1 Pydantic Models

**File**: `src/mcp_this/openapi_tools.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any

class AuthConfig(BaseModel):
    type: str = Field(..., regex="^(bearer|api_key|basic)$")
    token: Optional[str] = None
    key_name: Optional[str] = None
    key_value: Optional[str] = None
    
    @validator('token')
    def validate_bearer_token(cls, v, values):
        if values.get('type') == 'bearer' and not v:
            raise ValueError('Bearer auth requires token')
        return v
    
    @validator('key_value')  
    def validate_api_key(cls, v, values):
        if values.get('type') == 'api_key' and not v:
            raise ValueError('API key auth requires key_value')
        return v

class RetryConfig(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    timeout: int = Field(default=30, ge=1, le=300)

class OpenAPIConfig(BaseModel):
    spec_url: str = Field(..., regex=r"^(https?://|file://)")
    base_url: Optional[str] = None
    auth: Optional[AuthConfig] = None
    retry: RetryConfig = RetryConfig()
    include_patterns: List[str] = []
    exclude_patterns: List[str] = []
    tool_prefix: Optional[str] = None

def validate_openapi_configs(configs: Dict[str, Any]) -> Dict[str, OpenAPIConfig]:
    validated_configs = {}
    for name, config in configs.items():
        try:
            validated_configs[name] = OpenAPIConfig(**config)
        except Exception as e:
            raise ValueError(f"Invalid OpenAPI config '{name}': {e}")
    return validated_configs
```

### 5.2 Update Main Validation

**File**: `src/mcp_this/mcp_server.py`

```python
def validate_config(config: dict) -> None:
    # ... existing validation
    
    # NEW: OpenAPI validation
    if 'openapi' in config:
        from mcp_this.openapi_tools import validate_openapi_configs
        validate_openapi_configs(config['openapi'])
```

## 🧪 Phase 6: Testing Strategy

### 6.1 Test Configuration

**File**: `tests/test_openapi_integration.py`

**Test with real OpenAPI specs**:
- Petstore API (public, no auth)
- JSONPlaceholder API (simple REST API)
- Mock server with authentication

**Key Test Cases**:
1. Configuration validation
2. OpenAPI spec fetching (URL and file)
3. Tool extraction and registration
4. Authentication handling
5. Tool execution end-to-end
6. Error handling (network failures, invalid specs)

### 6.2 Mock FastMCP for Unit Tests

```python
# For unit tests, mock FastMCP responses
from unittest.mock import AsyncMock, Mock

async def test_tool_extraction():
    mock_fastmcp_server = Mock()
    mock_fastmcp_server.get_tools = AsyncMock(return_value={
        'test_tool': Mock(
            description='Test tool',
            inputSchema={'properties': {'param1': {'type': 'string'}}},
            run=AsyncMock(return_value=Mock(content=[Mock(text='result')]))
        )
    })
    
    # Test extraction logic
```

## 📚 Phase 7: Documentation and Examples

### 7.1 Update README.md

Add comprehensive OpenAPI examples:

```yaml
# Real-world example configurations
openapi:
  # Public API (no auth)
  petstore:
    spec_url: "https://petstore.swagger.io/v2/swagger.json"
    include_patterns: ["^/pet", "^/store"]
    
  # Internal API with authentication
  internal_api:
    spec_url: "https://api.company.com/openapi.json"
    auth:
      type: "bearer"
      token: "${COMPANY_API_TOKEN}"
    retry:
      max_attempts: 5
      timeout: 60
    exclude_patterns: ["^/admin", "^/internal"]
```

### 7.2 Create Example Configuration

**File**: `configs/openapi_example.yaml`

Include working examples with real APIs that can be tested.

## 🚨 Critical Implementation Notes

### Environment Variable Resolution

**Must handle**: `${ENV_VAR}` syntax in configuration:
```python
def resolve_auth_value(self, value: str) -> str:
    if value.startswith('${') and value.endswith('}'):
        env_var = value[2:-1]
        env_value = os.getenv(env_var)
        if env_value is None:
            raise ValueError(f"Environment variable {env_var} not found")
        return env_value
    return value
```

### Function Name Safety

**Must sanitize**: Tool names for Python function names:
```python
function_name = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name)
```

### FastMCP Tool Storage

**Critical**: Store FastMCP tools for execution:
```python
# In tool_info dict:
'fastmcp_tool': fastmcp_tool,  # The actual FastMCP tool instance
'execution_type': 'fastmcp',   # Flag for registration logic
```

### Async Context Handling

**Important**: All OpenAPI operations are async, ensure proper async context in mcp-this integration.

## 🎯 Success Criteria

- [ ] OpenAPI specs load from URLs and local files
- [ ] Tools generate with proper parameter handling  
- [ ] Authentication works (bearer, API key)
- [ ] Include/exclude patterns filter endpoints correctly
- [ ] Generated tools execute HTTP requests successfully
- [ ] Error handling provides clear user feedback
- [ ] Integration maintains mcp-this architecture patterns

## 📋 Implementation Order

1. **Phase 1**: Dependencies and basic structure
2. **Phase 2**: Tool extraction using FastMCP  
3. **Phase 3**: Tool execution bridge
4. **Phase 4**: Integration with mcp-this registration
5. **Phase 5**: Configuration validation
6. **Phase 6**: Testing implementation
7. **Phase 7**: Documentation and examples

**Estimated Effort**: 2-3 days for core implementation, 1-2 days for testing and documentation.

## 🔧 AI Agent Instructions

1. **Start with Phase 1** - get dependencies and basic structure working
2. **Focus on FastMCP integration patterns** - these are proven and tested
3. **Maintain existing mcp-this patterns** - don't change the core architecture
4. **Test incrementally** - verify each phase works before moving to the next
5. **Use the exact FastMCP imports and patterns** shown in this document
6. **Handle errors gracefully** - provide clear feedback for configuration issues
7. **Follow the existing code style** in mcp-this codebase

The key insight is that FastMCP does all the heavy lifting - we just need to extract the tools it creates and integrate them into mcp-this's registration system.
