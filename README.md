# `mcp-this`

> An MCP Server that dynamically exposes CLI/bash commands as tools through YAML configuration files.

`mcp-this` is an MCP server that dynamically exposes CLI/bash commands as tools for MCP Clients (e.g. Claude Desktop), based on definitions in YAML or JSON configuration files. Rather than requiring you to write code, you simply define the commands, their parameters, and execution details in configuration files, and the server makes them available as tools that clients can use.

For example, the following snippet shows a yaml file that defines three tools:

- `get-directory-tree` (via `tree` command)
- `find-files` (via `find` command)
- `web-scraper` (via `lynx` command)

```yaml
tools:
  get-directory-tree:
    description: Generate a directory tree
    execution:
      command: >-
        tree '<<directory>>'
        -a --gitignore
        -I ".git|.claude|.env|.venv|env|node_modules|__pycache__|.DS_Store|*.pyc<<custom_excludes>>"
        <<format_args>>
    parameters:
      directory:
        description: Directory to generate tree for.
        required: true
      custom_excludes:
        description: Additional patterns to exclude (begin with | e.g., "|build|dist").
        required: false
      format_args:
        description: Additional formatting arguments (e.g., "-L 3 -C --dirsfirst")
        required: false

  find-files:
    description: Locate files by name, pattern, type, size, date, or other criteria
    execution:
      command: find '<<directory>>' -type f <<arguments>> | sort
    parameters:
      directory:
        description: Directory to search in (quotes are handled automatically in the command)
        required: true
      arguments:
        description: Additional find arguments (e.g., "-name *.py -mtime -7 -not -path */venv/*")
        required: false

  web-scraper:
    description: Fetch a webpage and convert it to clean, readable text using lynx      
    execution:
      command: lynx -dump -nomargins -hiddenlinks=ignore <<dump_options>> '<<url>>'
    parameters:
      url:
        description: URL of the webpage to fetch and convert to text
        required: true
      dump_options:
        description: Additional lynx options (e.g., -width=100, -nolist, -source)
        required: false
```

If the file above was saved to `/path/to/your/custom_tools.yaml`, the corresponding MCP server config file (e.g. for Claude Desktop) would look like:

```json
{
  "mcpServers": {
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

## Features

- **Dynamically create MCP tools** from YAML configuration files
- **Define command-line tools** with parameters and execution details
- **Default configuration** with common utility tools ready to use
- **JSON configuration support** for programmatic use

## Quick Start

### `uvx`

The simplest way to use the server is via `uvx`. This command lets you run Python tools without installing them globally. It creates a temporary environment just for that tool, runs it, and then cleans up.

> **Note:** Examples below require installation of `uvx` - instructions can be found at [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/).

### Configuration

The MCP Server can be configured to use:
- Custom tools defined in a YAML file via the `--tools_path` command
- Custom tools via a JSON string with the `--tools` command
- Default tools from `./src/mcp_this/configs/default.yaml` if no configuration is provided

## Claude Desktop Integration

### Setting Up MCP-This with Claude Desktop

1. Start Claude Desktop
2. Navigate to `Settings -> Developer` and click "Edit Config"
3. Open `claude_desktop_config.json` in your editor of choice

### Using Default Tools

When neither `--tools` nor `--tools_path` options are used, the server will use the default tools defined in `./src/mcp_this/configs/default.yaml`.

**Step 1:** Replace/modify contents of `claude_desktop_config.json` with:

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

**Step 1.1:** 

A few of the default tools use commands that may not be installed on your machine (e.g. `tree`, `lynx`). See [Default Tools](#default-tools) and [Default Tool Dependencies](#default-tool-dependencies) sections below.

**Step 2:** Restart Claude Desktop

You should now see the `mcp-this-default` MCP server:

<img src="./documentation/images/server-default.png" alt="Claude Desktop showing mcp-this-default server" width="400">

**Step 3:** View and enable the tools by clicking on the server:

<img src="./documentation/images/default-tools.png" alt="Default tools available in mcp-this" width="350">

> **Troubleshooting:** If you see a `spawn uvx: ENOENT` or similar message:
> - Make sure you have `uvx` installed
> - Ensure `uvx` is in your `PATH` or use the full path (e.g., `/Users/<username>/.local/bin/uvx`)
> - Check that dependencies for tools are installed (see [Default Tool Dependencies](#default-tool-dependencies))

### Creating Custom Tools with YAML

**Step 1:** Create a file called `custom_tools.yaml` with these contents:

```yaml
tools:
  get-current-time:
    description: |
      Display the current date and time in various formats.
      
      If no format is specified, all formats will be displayed.

      Examples:
      - get_current_time(format="iso")
      - get_current_time(format="readable")
      - get_current_time(format="unix")
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

This yaml defines a single tool that will print out the current date/time in different formats. For example, `format=iso` will give `2025-05-18T17:17:39Z`.

**Step 2:** Configure Claude Desktop to run both default and custom tools:

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

**Step 3:** Restart Claude Desktop to see both servers:

<img src="./documentation/images/servers-default-custom.png" alt="Claude Desktop showing both default and custom servers" width="400">

**Step 4:** Enable and use your custom tool:

<img src="./documentation/images/custom-tool.png" alt="Custom get-current-time tool" width="350">

When using the tool in Claude Desktop, you will see something like:

<img src="./documentation/images/custom-tool-example.png" alt="Example of using the custom time tool" width="500">

### Configuring with a JSON String

You can also pass a JSON string containing tool definitions directly:

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

Configuration can be provided as either a YAML file or a JSON string. The format supports both top-level tools and organized toolsets.

### Basic Structure

The example below shows the definition of a single tool called `tool-name`. The command that this tool will execute is `command-to-execute <<parameter_name>>`. `<<parameter_name>>` will be replaced with the corresponding value passed by the MCP Client (e.g. `session.call_tool('tool-name',{'parameter_name': 'This is the param value that will be passed to the tool'})`).

For optional parameters (`required: false`), if the MCP client does not the parameter, the `<<parameter_name>>` will be removed before executing the command.

```yaml
tools:
  tool-name:
    description: "Description of what the tool does"
    execution:
      command: "command-to-execute <<parameter_name>>"
    parameters:
      parameter_name:
        description: "Description of the parameter"
        required: true
```

### Tool Configuration

Each tool requires the following configuration:

| Component | Description |
|-----------|-------------|
| **description** | Human-readable description of the tool with examples |
| **execution** | Command template with parameter placeholders (`<<parameter>>`) |
| **parameters** | Definitions for each parameter the tool accepts |

Parameters are specified in the form `<<parameter_name>>` in the command template and will be replaced with the actual parameter values when executed.

## Default Tools

The default configuration includes these powerful CLI tools:

| Tool | Description |
|------|-------------|
| **get-directory-tree** | Generate a directory tree with standard exclusions and gitignore support |
| **find-files** | Locate files by name, pattern, type, size, date, or other criteria |
| **find-text-patterns** | Search for text patterns in files with context and filtering |
| **extract-file-text** | Display file contents with options for line numbers or filtering |
| **extract-code-info** | Analyze code files to extract functions, classes, imports, and TODOs |
| **edit-file** | Modify files with precise control (insert, replace, delete) |
| **create-file** | Create new files with specified content |
| **create-directory** | Create new directories or directory structures |
| **web-scraper** | Fetch webpages and convert to clean, readable text |

### Default Tool Dependencies

For the default tools to work correctly, install the following dependencies:

**macOS:**
```bash
brew install tree  # Required for get-directory-tree
brew install lynx  # Required for web-scraper
```

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

### Defining Custom Tools in Python

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
    args=['-m', 'mcp_this', '--tools', json.dumps(toolset_config)],
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

| Method | Example |
|--------|---------|
| **Config File Path** | `--tools_path /path/to/config.yaml` |
| **Config Value String** | `--tools '{"tools": {...}}'` |
| **Environment Variable** | `MCP_THIS_CONFIG_PATH=/path/to/config.yaml` |
| **Default Config** | If no configuration is provided, the default tools are used |

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
