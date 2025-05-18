# MCP-This

> An MCP Server that dynamically exposes CLI commands as tools through YAML configuration files.

`mcp-this` creates MCP tools from configuration files, allowing Claude to execute CLI commands without requiring you to write any code. Simply define which commands should be exposed as tools, along with their parameters and execution details, in a YAML or JSON format.

## Features

- Dynamically create MCP tools from a YAML configuration file
- Define command-line tools with parameters and execution details
- Default configuration with common utility tools
- Support for JSON configuration string for programmatic use
- Compatible with Claude Desktop and Claude MCP API

## Installation

```bash
# Install using uv (recommended)
uv install mcp-this

# Or with pip
pip install mcp-this
```

## Quick Start

### Using the Default Tools

```bash
# Start the MCP server with default tools
uvx mcp-this

# Or using the MCP framework
mcp dev -m mcp_this
```

### Using Custom Tools

```bash
# Using a custom configuration file
uvx mcp-this --config_path ./my_config.yaml

# Using the MCP framework with a custom configuration
mcp dev -m mcp_this --config_path ./my_config.yaml
```

### Using with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "mcp-this-default": {
      "command": "uvx",
      "args": ["mcp-this"]
    },
    "mcp-this-custom": {
      "command": "uvx",
      "args": [
        "mcp-this",
        "--config_path",
        "./my_config.yaml"
      ]
    }
  }
}
```

## Configuration Format

Configuration can be provided either as a YAML file or a JSON string. The format supports both top-level tools and organized toolsets.

### Basic Structure

```yaml
# Option 1: Define tools at the top level
tools:
  tool-name:
    description: "Description of what the tool does"
    execution:
      command: "command-to-execute <<parameter>>"
    parameters:
      parameter:
        description: "Description of the parameter"
        required: true

# Option 2: Organize tools into toolsets
toolsets:
  toolset-name:
    description: "Description of the toolset"
    tools:
      tool-name:
        description: "Description of what the tool does"
        execution:
          command: "command-to-execute <<parameter>>"
        parameters:
          parameter:
            description: "Description of the parameter"
            required: true
```

### Tool Configuration

Each tool requires the following configuration:

- **description**: Human-readable description of the tool
- **execution**: Command template with parameter placeholders (`<<parameter>>`)
- **parameters**: Definitions for each parameter the tool accepts

Parameters are specified in the form `<<parameter_name>>` in the command template and will be replaced with the actual parameter values when executed.

## Default Tools

The following tools are included in the default configuration:

- `get-directory-tree`: Generate a directory tree with standard exclusions
- `find-files`: Locate files by name, pattern, type, and other criteria
- `find-text-patterns`: Search for text patterns in files with context and filtering
- `extract-file-text`: Display file contents with options for line numbers or filtering
- `extract-code-info`: Analyze code files to extract functions, classes, imports, and TODOs
- `edit-file`: Modify files with precise control (insert, replace, delete)
- `create-file`: Create new files with specified content
- `create-directory`: Create new directories or directory structures
- `web-scraper`: Fetch webpages and convert to clean, readable text

### Default Tool Dependencies

For the default tools to work correctly, the following dependencies are required:

**Mac:**
```bash
brew install tree
brew install lynx
```

- `tree` - Used by `get-directory-tree`
- `lynx` - Used by `web-scraper`

## Usage Examples

### Python Client API

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Start server with default configuration
server_params = StdioServerParameters(
    command='python',
    args=['-m', 'mcp_this'],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # List available tools
        tools = await session.list_tools()
        for tool in tools.tools:
            print(f"- {tool.name}")
        
        # Call a tool
        dir_tree_result = await session.call_tool(
            'get-directory-tree',
            {'directory': '/path/to/project'},
        )
        print(dir_tree_result.content[0].text)
```

### Defining Custom Tools

```python
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Define custom tools
toolset_config = {
    'tools': {
        'extract-html-text': {
            'description': "Fetch a webpage and extract pure text, removing HTML tags",
            'execution': {
                'command': "curl -s <<url>> | sed '/<style/,/<\\/style>/d; /<script/,/<\\/script>/d' | sed 's/<[^>]*>//g'",
            },
            'parameters': {
                'url': {
                    'description': "URL of the webpage to fetch",
                    'required': True,
                },
            },
        },
    },
}

# Start server with custom configuration
server_params = StdioServerParameters(
    command='python',
    args=['-m', 'mcp_this', '--config_value', json.dumps(toolset_config)],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # Call custom tool
        result = await session.call_tool(
            'extract-html-text',
            {'url': 'https://example.com'},
        )
        print(result.content[0].text)
```

## Configuration Methods

You can provide configuration in several ways:

1. **Config File Path**: `--config_path /path/to/config.yaml`
2. **Config Value String**: `--config_value '{"tools": {...}}'`
3. **Environment Variable**: `MCP_THIS_CONFIG_PATH=/path/to/config.yaml`
4. **Default Config**: If no configuration is provided, the default configuration is used

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-username/mcp-this.git
cd mcp-this

# Install dependencies
uv sync
```

### Running Tests

```bash
# Run all tests, including linting
make tests

# Run only unit tests
make unittests

# Run only linting checks
make linting

# View test coverage
make open_coverage
```

### Building and Publishing the Package

```bash
# Build the package
make package-build

# Publish the package (requires UV_PUBLISH_TOKEN)
make package-publish
```

### Adding Dependencies

```bash
# Add a regular dependency
uv add <package>

# Add a development dependency
uv add <package> --group dev
```

## License

[Apache License 2.0](LICENSE)