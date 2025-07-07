# 🚀 Implementation Plan: OpenAPI Integration for mcp-this
*REVISED: Critical Issues Addressed*

## 🚨 Critical Design Issues Identified & Resolved

### **Issue 1: FastMCP Integration Approach**
**Problem**: `FastMCP.from_openapi()` creates a complete MCP server, not just parsed tools. We can't easily extract individual tools from it.

**Solution**: Use FastMCP's underlying OpenAPI parsing libraries directly, or create a hybrid approach where we use FastMCP's parsing logic but integrate with our tool registration system.

### **Issue 2: Async Context Conflicts**  
**Problem**: Using `asyncio.run()` inside `register_all()` can cause issues if we're already in an async context.

**Solution**: Make `register_all()` async and handle OpenAPI parsing at the right level.

### **Issue 3: Tool Registration Pattern Mismatch**
**Problem**: Current pattern creates `ToolInfo` objects then registers them. FastMCP creates tools differently.

**Solution**: Create `ApiToolInfo` objects that follow the same pattern as `ToolInfo` but execute HTTP requests instead of shell commands.

---

## **Phase 1: Core Architecture Setup**

### **1.1 New Dependencies**
Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing deps
    "httpx>=0.24.0",           # HTTP client for API calls
    "tenacity>=8.0.0",         # For retries/backoff
    "jsonref>=1.1.0",          # Handle OpenAPI $ref resolution
    "openapi-spec-validator>=0.6.0",  # Validate OpenAPI specs
]
```

**Note**: We're NOT adding FastMCP as a dependency. We'll implement our own OpenAPI parsing to maintain architectural consistency.

### **1.2 New File Structure**
```
src/mcp_this/
├── api_tools.py          # NEW: OpenAPI tool parsing and execution
├── configs/
│   ├── openapi_example.yaml  # NEW: Example OpenAPI config
└── # ... existing files
```

## **Phase 2: Configuration Schema Design**

### **2.1 YAML Configuration Format**
```yaml
# Enhanced mcp-this configuration
openapi:
  my_api:
    spec_url: "https://api.example.com/openapi.json"
    base_url: "https://api.example.com"  # Optional override
    
    # Authentication (flexible approach)
    auth:
      type: "bearer" 
      token: "${API_TOKEN}"  # Environment variable (preferred)
      # token: "hardcoded-for-testing"  # Direct value (testing only)
    
    # Retry configuration  
    retry:
      max_attempts: 3
      backoff_factor: 2
      timeout: 30
    
    # Endpoint filtering (both optional)
    include_patterns: ["^/api/v1", "^/public"]
    exclude_patterns: ["^/admin", "^/internal"]
    
    # Tool naming (optional)
    tool_prefix: "api"  # Custom prefix instead of config name
    
    # Route type mapping (default: all endpoints become tools)
    convert_gets_to_tools: true  # Force GET endpoints to be tools instead of resources

  another_api:
    spec_url: "file:///path/to/local/spec.json"
    auth:
      type: "api_key"
      key_name: "X-API-Key"
      key_value: "${ANOTHER_API_KEY}"

# Existing sections work unchanged
tools:
  my-cli-tool:
    # ... existing CLI tools

prompts:
  # ... existing prompts
```

### **2.2 Tool Naming Convention**
- **Format**: `{config_name}__{method}_{endpoint_path_simplified}`
- **Examples**:
  - `GET /users/{id}` → `my_api__get_users_id(user_id: str)`
  - `POST /items` → `my_api__post_items(request_body: str = "")`
  - With custom prefix: `api__get_users_id(user_id: str)`

## **Phase 3: Implementation Strategy**

### **3.1 New Module: `api_tools.py`**
```python
"""OpenAPI tool parsing and execution for MCP server."""
import json
import re
import os
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import httpx
import asyncio
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential
import yaml


@dataclass
class ApiToolInfo:
    """Information about an API tool parsed from OpenAPI specification."""
    
    config_name: str
    tool_name: str
    function_name: str
    method: str
    endpoint_path: str
    base_url: str
    description: str
    parameters: dict[str, dict]
    param_string: str
    exec_code: str
    runtime_info: dict[str, any]

    def get_full_description(self) -> str:
        """Generate LLM-optimized description for API tools."""
        lines = []
        
        lines.append("API TOOL DESCRIPTION:")
        lines.append("")
        lines.append(self.description.strip())
        
        lines.append("")
        lines.append("API ENDPOINT:")
        lines.append("")
        lines.append(f"`{self.method} {self.endpoint_path}`")
        lines.append(f"Base URL: {self.base_url}")
        
        if self.parameters:
            lines.append("")
            lines.append("PARAMETERS:")
            lines.append("")
            
            for param_name, param_config in self.parameters.items():
                desc = param_config.get("description", "")
                required = param_config.get("required", False)
                param_type = param_config.get("type", "string")
                param_in = param_config.get("in", "body")
                
                req_status = "[REQUIRED]" if required else "[OPTIONAL]"
                type_info = f"({param_type}, {param_in})"
                
                lines.append(f"- {param_name} {req_status} {type_info}: {desc}")
        
        return "\n".join(lines)


# Key functions to implement
async def fetch_openapi_spec(spec_url: str) -> dict:
    """Fetch and parse OpenAPI specification from URL or file."""
    
async def parse_openapi_configs(openapi_configs: dict) -> list[ApiToolInfo]:
    """Parse all OpenAPI configurations and return list of ApiToolInfo objects."""

def create_api_tool_info(config_name: str, operation_info: dict, config: dict) -> ApiToolInfo:
    """Create ApiToolInfo from OpenAPI operation definition."""

async def execute_api_request(runtime_info: dict, parameters: dict) -> str:
    """Execute HTTP API request with authentication and retry logic."""

def resolve_auth_value(value: str) -> str:
    """Handle environment variable substitution."""

def validate_openapi_configs(openapi_configs: dict) -> None:
    """Validate OpenAPI configuration section."""
```

### **3.2 Integration with Existing Architecture**

**Update `mcp_server.py`:**
```python
# Add import
from mcp_this.api_tools import parse_openapi_configs, register_api_tools

# Make register_all async
async def register_all(config: dict) -> None:
    """Register CLI tools, prompts, and API tools from configuration."""
    
    # Existing registrations
    if 'tools' in config:
        register_tools(config)
    if 'prompts' in config:
        prompts_info = parse_prompts(config)
        register_prompts(prompts_info)
    
    # NEW: Register OpenAPI tools
    if 'openapi' in config:
        api_tools_info = await parse_openapi_configs(config['openapi'])
        register_api_tools(api_tools_info)

# Update validate_config
def validate_config(config: dict) -> None:
    """Enhanced validation including OpenAPI section."""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")

    # Check if we have at least one section
    if not any(section in config for section in ['tools', 'prompts', 'openapi']):
        raise ValueError("Configuration must contain 'tools', 'prompts', and/or 'openapi' sections")

    # Existing validations...
    if 'tools' in config:
        # ... existing tool validation
        pass
    if 'prompts' in config:
        # ... existing prompt validation  
        pass
    
    # NEW: OpenAPI validation
    if 'openapi' in config:
        from mcp_this.api_tools import validate_openapi_configs
        validate_openapi_configs(config['openapi'])

# Update init_server to handle async
def init_server(config_path: str | None = None, tools: str | None = None) -> None:
    """Initialize the server with the given configuration."""
    config = load_config(config_path, tools)
    validate_config(config)
    
    # Handle async registration
    import asyncio
    asyncio.run(register_all(config))
```

### **3.3 OpenAPI Parsing Implementation**

**Core parsing logic:**
```python
async def parse_openapi_configs(openapi_configs: dict) -> list[ApiToolInfo]:
    """Parse multiple OpenAPI configurations."""
    all_api_tools = []
    
    for config_name, api_config in openapi_configs.items():
        try:
            tools = await parse_single_openapi_config(config_name, api_config)
            all_api_tools.extend(tools)
        except Exception as e:
            print(f"Error parsing OpenAPI config '{config_name}': {e}")
            # Continue with other configs
    
    return all_api_tools

async def parse_single_openapi_config(config_name: str, api_config: dict) -> list[ApiToolInfo]:
    """Parse one OpenAPI config into ApiToolInfo objects."""
    
    # 1. Fetch OpenAPI spec
    spec = await fetch_openapi_spec(api_config['spec_url'])
    
    # 2. Validate spec
    validate_openapi_spec(spec)
    
    # 3. Get base URL
    base_url = api_config.get('base_url') or get_base_url_from_spec(spec)
    
    # 4. Parse endpoints
    api_tools = []
    for path, path_item in spec.get('paths', {}).items():
        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue
                
            # Apply include/exclude filters
            if not should_include_endpoint(path, method, api_config):
                continue
            
            # Create tool info
            tool_info = create_api_tool_info_from_operation(
                config_name=config_name,
                path=path,
                method=method,
                operation=operation,
                config=api_config,
                base_url=base_url
            )
            api_tools.append(tool_info)
    
    return api_tools

def create_api_tool_info_from_operation(
    config_name: str, 
    path: str, 
    method: str, 
    operation: dict, 
    config: dict,
    base_url: str
) -> ApiToolInfo:
    """Create ApiToolInfo from OpenAPI operation."""
    
    # Generate tool name
    tool_prefix = config.get('tool_prefix', config_name)
    operation_id = operation.get('operationId')
    
    if operation_id:
        tool_name = f"{tool_prefix}__{operation_id}"
    else:
        # Generate from method + path
        path_clean = re.sub(r'[^a-zA-Z0-9_]', '_', path.strip('/').replace('/', '_'))
        tool_name = f"{tool_prefix}__{method.lower()}_{path_clean}"
    
    function_name = re.sub(r'[^a-zA-Z0-9_]', '_', tool_name)
    
    # Parse parameters
    parameters = {}
    required_params = []
    optional_params = []
    
    # Handle OpenAPI parameters
    for param in operation.get('parameters', []):
        param_name = param['name']
        param_info = convert_openapi_parameter(param)
        parameters[param_name] = param_info
        
        if param.get('required', False):
            required_params.append(param_name)
        else:
            optional_params.append(f"{param_name}: str = ''")
    
    # Handle request body for POST/PUT/PATCH
    if 'requestBody' in operation and method.upper() in ['POST', 'PUT', 'PATCH']:
        parameters['request_body'] = {
            'description': 'Request body as JSON string',
            'required': operation['requestBody'].get('required', False),
            'type': 'string',
            'in': 'body'
        }
        if operation['requestBody'].get('required', False):
            required_params.append('request_body')
        else:
            optional_params.append('request_body: str = ""')
    
    param_string = ", ".join(required_params + optional_params)
    
    # Generate execution code
    exec_code = generate_api_function_code(function_name, param_string)
    
    # Create runtime info
    runtime_info = {
        "config_name": config_name,
        "method": method.upper(),
        "endpoint_path": path,
        "base_url": base_url,
        "auth_config": config.get('auth'),
        "retry_config": config.get('retry', {}),
        "parameter_specs": parameters,
    }
    
    return ApiToolInfo(
        config_name=config_name,
        tool_name=tool_name,
        function_name=function_name,
        method=method.upper(),
        endpoint_path=path,
        base_url=base_url,
        description=operation.get('description', operation.get('summary', f'{method.upper()} {path}')),
        parameters=parameters,
        param_string=param_string,
        exec_code=exec_code,
        runtime_info=runtime_info,
    )
```

## **Phase 4: Security Implementation**

### **4.1 Authentication Handling**
```python
def resolve_auth_value(value: str) -> str:
    """Handle environment variable substitution and direct values."""
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        env_var = value[2:-1]
        env_value = os.getenv(env_var)
        if env_value is None:
            raise ValueError(f"Environment variable {env_var} not found")
        return env_value
    return value  # Return as-is (direct value for testing)

def apply_authentication(headers: dict, auth_config: dict) -> None:
    """Apply authentication to HTTP request headers."""
    if not auth_config:
        return
        
    auth_type = auth_config.get('type')
    
    if auth_type == 'bearer':
        token = resolve_auth_value(auth_config['token'])
        headers['Authorization'] = f'Bearer {token}'
    elif auth_type == 'api_key':
        key_name = auth_config.get('key_name', 'X-API-Key')
        key_value = resolve_auth_value(auth_config['key_value'])
        headers[key_name] = key_value
    elif auth_type == 'basic':
        username = resolve_auth_value(auth_config.get('username', ''))
        password = resolve_auth_value(auth_config.get('password', ''))
        import base64
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers['Authorization'] = f'Basic {credentials}'
    else:
        raise ValueError(f"Unsupported auth type: {auth_type}")
```

### **4.2 Retry Logic with Tenacity**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

async def execute_api_request(runtime_info: dict, parameters: dict) -> str:
    """Execute API request with configurable retry logic."""
    
    retry_config = runtime_info.get('retry_config', {})
    max_attempts = retry_config.get('max_attempts', 3)
    backoff_factor = retry_config.get('backoff_factor', 2)
    timeout = retry_config.get('timeout', 30)
    
    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=backoff_factor, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    async def _make_request():
        return await _execute_api_request_once(runtime_info, parameters, timeout)
    
    try:
        return await _make_request()
    except Exception as e:
        return f"API Error after {max_attempts} attempts: {str(e)}"

async def _execute_api_request_once(runtime_info: dict, parameters: dict, timeout: int) -> str:
    """Execute single API request attempt."""
    method = runtime_info['method']
    base_url = runtime_info['base_url']
    endpoint_path = runtime_info['endpoint_path']
    auth_config = runtime_info.get('auth_config')
    param_specs = runtime_info['parameter_specs']
    
    # Build URL with path parameters
    url = urljoin(base_url.rstrip('/') + '/', endpoint_path.lstrip('/'))
    for param_name, param_value in parameters.items():
        if param_value and param_specs.get(param_name, {}).get('in') == 'path':
            url = url.replace(f'{{{param_name}}}', str(param_value))
    
    # Build query parameters
    query_params = {}
    for param_name, param_value in parameters.items():
        if param_value and param_specs.get(param_name, {}).get('in') == 'query':
            query_params[param_name] = param_value
    
    # Build headers
    headers = {'User-Agent': 'mcp-this/1.0'}
    for param_name, param_value in parameters.items():
        if param_value and param_specs.get(param_name, {}).get('in') == 'header':
            headers[param_name] = param_value
    
    # Apply authentication
    if auth_config:
        apply_authentication(headers, auth_config)
    
    # Handle request body
    json_data = None
    if method in ['POST', 'PUT', 'PATCH']:
        body_param = parameters.get('request_body')
        if body_param:
            headers['Content-Type'] = 'application/json'
            try:
                json_data = json.loads(body_param) if isinstance(body_param, str) else body_param
            except json.JSONDecodeError:
                return f"Error: Invalid JSON in request_body: {body_param}"
    
    # Make the API request
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method=method,
            url=url,
            params=query_params,
            headers=headers,
            json=json_data
        )
        
        # Format response for LLM consumption
        result_lines = [
            f"HTTP {response.status_code} {response.reason_phrase}",
            f"URL: {method} {response.url}",
        ]
        
        if response.status_code >= 400:
            result_lines.append(f"Error: {response.status_code} {response.reason_phrase}")
        
        # Add response body
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            try:
                json_response = response.json()
                result_lines.append("\nResponse:")
                result_lines.append(json.dumps(json_response, indent=2))
            except:
                result_lines.append(f"\nResponse: {response.text}")
        else:
            result_lines.append(f"\nResponse: {response.text}")
            
        return "\n".join(result_lines)
```

## **Phase 5: Tool Generation Strategy**

### **5.1 Dynamic Function Generation** 
Follows the same pattern as existing CLI tools:

```python
def generate_api_function_code(function_name: str, param_string: str) -> str:
    """Generate function code for API tool (similar to tools.py pattern)."""
    
    return f"""async def {function_name}({param_string}) -> str:
    \"\"\"API endpoint tool generated from OpenAPI specification.\"\"\"
    # Get runtime info for this API tool
    runtime_info = tool_info
    # Collect all parameters
    params = {{}}
    {generate_param_collection_code(param_string)}
    # Execute API request with retries
    return await execute_api_request(runtime_info, params)
"""

def generate_param_collection_code(param_string: str) -> str:
    """Generate parameter collection code."""
    if not param_string:
        return ""
    
    param_names = []
    for param in param_string.split(','):
        param_name = param.split(':')[0].strip()
        param_names.append(param_name)
    
    collection_lines = []
    for param_name in param_names:
        collection_lines.append(f"    params['{param_name}'] = {param_name}")
    
    return "\n".join(collection_lines)

def register_api_tools(api_tools_info: list[ApiToolInfo]) -> None:
    """Register API tools with MCP (follows existing pattern in mcp_server.py)."""
    from mcp_this.mcp_server import mcp
    
    for api_tool in api_tools_info:
        try:
            # Create namespace for the generated function
            tool_namespace = {
                "tool_info": api_tool.runtime_info,
                "execute_api_request": execute_api_request,
            }
            
            # Execute the code to create the function 
            exec(api_tool.exec_code, tool_namespace)
            
            # Get the created function
            handler = tool_namespace[api_tool.function_name]
            
            # Register with MCP (same pattern as CLI tools)
            mcp.tool(
                name=api_tool.tool_name,
                description=api_tool.get_full_description(),
            )(handler)
            
        except Exception as e:
            print(f"Error registering API tool {api_tool.tool_name}: {e}")
```

## **Phase 6: Error Handling & Validation**

### **6.1 Startup Validation**
```python
def validate_openapi_configs(openapi_configs: dict) -> None:
    """Validate OpenAPI configuration section during startup."""
    if not isinstance(openapi_configs, dict):
        raise ValueError("'openapi' must be a dictionary")
    
    for config_name, api_config in openapi_configs.items():
        if not isinstance(api_config, dict):
            raise ValueError(f"OpenAPI config '{config_name}' must be a dictionary")
        
        if 'spec_url' not in api_config:
            raise ValueError(f"OpenAPI config '{config_name}' missing required 'spec_url'")
        
        # Validate auth configuration
        if 'auth' in api_config:
            validate_auth_config(config_name, api_config['auth'])
        
        # Validate retry configuration
        if 'retry' in api_config:
            validate_retry_config(config_name, api_config['retry'])

def validate_auth_config(config_name: str, auth_config: dict) -> None:
    """Validate authentication configuration."""
    auth_type = auth_config.get('type')
    if auth_type not in ['bearer', 'api_key', 'basic']:
        raise ValueError(f"OpenAPI config '{config_name}': Unsupported auth type '{auth_type}'")
    
    # Check for required fields per auth type
    if auth_type == 'bearer' and 'token' not in auth_config:
        raise ValueError(f"OpenAPI config '{config_name}': Bearer auth requires 'token'")
    elif auth_type == 'api_key':
        if 'key_value' not in auth_config:
            raise ValueError(f"OpenAPI config '{config_name}': API key auth requires 'key_value'")
    elif auth_type == 'basic':
        if 'username' not in auth_config or 'password' not in auth_config:
            raise ValueError(f"OpenAPI config '{config_name}': Basic auth requires 'username' and 'password'")

def validate_retry_config(config_name: str, retry_config: dict) -> None:
    """Validate retry configuration."""
    if 'max_attempts' in retry_config:
        if not isinstance(retry_config['max_attempts'], int) or retry_config['max_attempts'] < 1:
            raise ValueError(f"OpenAPI config '{config_name}': max_attempts must be positive integer")
    
    if 'timeout' in retry_config:
        if not isinstance(retry_config['timeout'], (int, float)) or retry_config['timeout'] <= 0:
            raise ValueError(f"OpenAPI config '{config_name}': timeout must be positive number")
```

### **6.2 Runtime Error Handling**
```python
async def fetch_openapi_spec(spec_url: str) -> dict:
    """Fetch OpenAPI spec with proper error handling."""
    try:
        if spec_url.startswith('file://'):
            # Handle local files
            file_path = spec_url[7:]  # Remove 'file://' prefix
            with open(file_path, 'r') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        else:
            # Handle URLs
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(spec_url)
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', '')
                if 'yaml' in content_type or spec_url.endswith(('.yaml', '.yml')):
                    return yaml.safe_load(response.text)
                else:
                    return response.json()
                    
    except FileNotFoundError:
        raise ValueError(f"OpenAPI spec file not found: {spec_url}")
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Failed to fetch OpenAPI spec from {spec_url}: {e.response.status_code}")
    except httpx.TimeoutException:
        raise ValueError(f"Timeout fetching OpenAPI spec from {spec_url}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in OpenAPI spec: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in OpenAPI spec: {e}")
    except Exception as e:
        raise ValueError(f"Error loading OpenAPI spec from {spec_url}: {e}")
```

## **Phase 7: Testing Strategy**

### **7.1 Test Configuration**
```yaml
# tests/fixtures/test_openapi_config.yaml
openapi:
  test_api:
    spec_url: "file://tests/fixtures/test_openapi_spec.json"
    auth:
      type: "bearer"
      token: "test-token"
    retry:
      max_attempts: 2
      timeout: 5
    include_patterns: ["^/test"]
```

### **7.2 Test Cases**
1. **Configuration parsing and validation tests**
2. **OpenAPI spec fetching tests (URL and file)**
3. **Tool generation from OpenAPI operations**
4. **Authentication handling tests**
5. **Retry logic tests with httpx mocking**
6. **Integration tests with mock HTTP servers**
7. **Error handling tests (network failures, invalid specs)**

## **Phase 8: Documentation & Examples**

### **8.1 Update README.md**
Add comprehensive OpenAPI examples:
```yaml
# Real-world example configurations
openapi:
  # Public API (no auth required)
  petstore:
    spec_url: "https://petstore.swagger.io/v2/swagger.json"
    include_patterns: ["^/pet", "^/store"]
    
  # Internal API with auth
  internal_api:
    spec_url: "https://api.company.com/openapi.json"
    auth:
      type: "bearer"
      token: "${COMPANY_API_TOKEN}"
    retry:
      max_attempts: 5
      timeout: 60
```

### **8.2 Example Configurations**
Create `configs/openapi_example.yaml` with working examples.

---

## 📝 Implementation Priority

1. **Phase 1**: Core architecture and dependencies
2. **Phase 2**: Configuration schema and validation  
3. **Phase 3**: Basic OpenAPI parsing and tool generation
4. **Phase 4**: Authentication and security
5. **Phase 5**: Retry logic and error handling
6. **Phase 6**: Comprehensive error handling
7. **Phase 7-8**: Testing and documentation

## 🔧 Success Criteria

- [ ] OpenAPI specs can be loaded from URLs and local files
- [ ] Tools are generated with proper parameter handling
- [ ] Authentication works for bearer, API key, and basic auth
- [ ] Retry logic handles network failures gracefully
- [ ] Configuration validation prevents invalid setups
- [ ] Generated tools follow same patterns as CLI tools
- [ ] Error messages are clear and actionable

This revised plan addresses all critical architectural issues while maintaining consistency with the existing mcp-this patterns.
