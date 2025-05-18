# MCP-This

> An MCP Server that dynamically exposes CLI commands as tools through YAML configuration files.

`mcp-this` creates MCP tools from configuration files, allowing Claude to execute CLI commands without requiring you to write any code. Simply define which commands should be exposed as tools, along with their parameters and execution details, in a YAML or JSON format.

## Features

- Dynamically create MCP tools from a YAML configuration file
- Define command-line tools with parameters and execution details
- Default configuration with common utility tools
- Support for JSON configuration string for programmatic use
- Compatible with Claude Desktop and Claude MCP API

# Quick Start

The simplest way to use the server is via `uvx`. `uvx` is a command that lets you run Python tools without installing them globally. It creates a temporary environment just for that tool, runs it, and then cleans up. Examples below require installation of `uvx` - instructions can be found here [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/).

## Claude Desktop

- Start Claude Desktop
- Navigate to `Settings->Developer`; click "Edit Config"
- Open `claude_desktop_config.json` in your editor of choice

### Using Default Tools

- The MCP Server can be configured to use custom tools defined in a yaml file via the `--tools_path` command or it can be given a single json string via `--tools`. 
- If neither are provided, the tools defined in `./src/mcp_this/configs/default.yaml` are used, which are:
    - TODO: list default tools with brief descriptions

    - Optionally install dependencies if you want to use the tools (see notes below)

The simplest way to get started is to use default tools and replace/modify contents of `claude_desktop_config.json` with:

```json
{
  "mcpServers": {
    "mcp-this-default": {
      "command": "uvx",
      "args": ["mcp-this"]
    }
  }
}
```

Then when you restart Claude you should see `mcp-this-default` mcp server:

<img src="./documentation/images/server-default.png" alt="Claude Desktop showing mcp-this-default server" width="300">

You can view the tools and enable/disable by clicking on the server:

<img src="./documentation/images/default-tools.png" alt="Claude Desktop showing mcp-this-default server" width="250">


NOTE: If you see a `spawn uvx: ENOENT` or similar message it could mean:
- you don't have `uvx` installed (see note above)
- `uvx` is installed but not in the `PATH`
    - add it to your `PATH` or use use the full path e.g. `/Users/<username>/.local/bin/uvx`


### Example Passing Yaml that Defines Tools

As mentioned above, the MCP Server can be configured to use custom tools defined in a yaml file via the `--tools_path` command.

- Create a file called `custom_tools.yaml` with these contents:

```yaml
tools:
  get-current-time:
    description: |
      Display the current date and time in various formats.
      
      Examples:
      - get_current_time(format="iso")
      - get_current_time(format="readable")
      - get_current_time(format="unix")

      If no format is specified, all formats will be displayed.
    execution:
      command: >-
        if [ "<<format>>" = "iso" ]; then 
          date -u +"%Y-%m-%dT%H:%M:%SZ"; 
        elif [ "<<format>>" = "readable" ]; then 
          date "+%A, %B %d, %Y %I:%M %p"; 
        elif [ "<<format>>" = "unix" ]; then 
          date +%s; 
        else 
          echo "ISO: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"; 
          echo "Readable: $(date "+%A, %B %d, %Y %I:%M %p")"; 
          echo "Unix timestamp: $(date +%s)"; 
        fi
    parameters:
      format:
        description: "Time format to display (iso, readable, unix, or leave empty for all formats)"
        required: false
```

> This tool will print out the current date/time e.g. `format=iso` will give `2025-05-18T17:17:39`.

- Replace/modify contents of `claude_desktop_config.json` with:
    - This will start two `mcp-this` servers, `mcp-this-default` and `mcp-this-custom`
        - `mcp-this-default`: This server does not specify any tools and will load the default tools described in the example above.
        - `mcp-this-custom`: This server defines a tool called `get-current-time`.

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
        "--tools_path", "/path/to/your/custom_tools.yaml"
      ]
    }
  }
}
```

<img src="./documentation/images/servers-default-custom.png" alt="Claude Desktop showing mcp-this-default server" width="300">

Which should have the following tool.

<img src="./documentation/images/custom-tool.png" alt="Claude Desktop showing mcp-this-default server" width="300">

When using the tool in Claude Desktop, you will see something like:

<img src="./documentation/images/custom-tool-example.png" alt="Claude Desktop showing mcp-this-default server" width="500">


### Example Passing Tools as JSON string

You can also pass a JSON string containing the tool definitions directly to the server. This is equivalent to the previous example where we passed the path to a yaml file.

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
        "--tools",
        "{\"tools\":{\"current-time\":{\"description\":\"Display the current date and time in various formats.\\n\\nExamples:\\n- current_time(format=\\\"iso\\\")  # ISO format (2023-05-18T14:30:45)\\n- current_time(format=\\\"readable\\\")  # Human readable (Thursday, May 18, 2023 2:30 PM)\\n- current_time(format=\\\"unix\\\")  # Unix timestamp (1684421445)\\n\\nIf no format is specified, all formats will be displayed.\",\"execution\":{\"command\":\"if [ \\\"<<format>>\\\" = \\\"iso\\\" ]; then date -u +\\\"%Y-%m-%dT%H:%M:%SZ\\\"; elif [ \\\"<<format>>\\\" = \\\"readable\\\" ]; then date \\\"+%A, %B %d, %Y %I:%M %p\\\"; elif [ \\\"<<format>>\\\" = \\\"unix\\\" ]; then date +%s; else echo \\\"ISO: $(date -u +\\\"%Y-%m-%dT%H:%M:%SZ\\\")\\\"; echo \\\"Readable: $(date \\\"+%A, %B %d, %Y %I:%M %p\\\")\\\"; echo \\\"Unix timestamp: $(date +%s)\\\"; fi\"},\"parameters\":{\"format\":{\"description\":\"Time format to display (iso, readable, unix, or leave empty for all formats)\",\"required\":false}}}}}"
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

1. **Config File Path**: `--tools_path /path/to/config.yaml`
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