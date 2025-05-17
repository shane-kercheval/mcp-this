# MCP-This

> MCP Server that exposes CLI commands as tools using YAML files.

`mcp-this` is an MCP server that makes command-line tools available to Claude via the Model-Control-Protocol. The server reads YAML configuration files to define which commands should be exposed as MCP tools, along with their parameters and execution details. This allows Claude to execute CLI commands without requiring you to write any code.

## 📋 Features

- 🔧 **Dynamic Tool Creation**: Define CLI tools in YAML without writing code
- 🔄 **Command Execution**: Execute shell commands with parameter substitution
- 📁 **Working Directory Support**: Run commands in specific directories
- 🧩 **Toolset Organization**: Group related tools into logical toolsets
- 🤖 **Claude Integration**: Seamless integration with Claude Desktop

## 🚀 Installation

### Using pip

```bash
pip install mcp-this
```

### Using uv (recommended)

```bash
uv pip install mcp-this
```

## 🏁 Quick Start

1. Create a YAML configuration file:

### Using top-level tools

```yaml
tools:
  curl:
    description: "Make HTTP requests"
    execution:
      command: "curl <<arguments>>"
    parameters:
      arguments:
        description: "Complete curl arguments including options and URL"
        required: true
```

### Using toolsets

A toolset is a way to organize groups of tools. In the future, toolsets could, for example, share settings like allow/deny lists. Toolsets could also be used, for example, to enable/disable/search for sets of tools.

```yaml
toolsets:
  curl:
    description: "Transfer data from or to a server"
    tools:
      curl:
        description: "Make HTTP requests"
        execution:
          command: "curl <<arguments>>"
        parameters:
          arguments:
            description: "Complete curl arguments including options and URL"
            required: true
```

2. Run the MCP server:

```bash
# Using tools path
mcp-this --tools-path /path/to/your/config.yaml

# Using JSON string directly
mcp-this --tools '{"tools": {"echo": {"description": "Echo command", "execution": {"command": "echo <<message>>"}, "parameters": {"message": {"description": "Message to echo", "required": true}}}}}'

# Using environment variable
export MCP_THIS_CONFIG_PATH=/path/to/your/config.yaml
mcp-this
```

## 🛠️ Configuration Structure

The configuration YAML files can follow one of two structures:

### Toolsets Format (Original)

This format organizes tools into logical groups called toolsets:

```yaml
toolsets:
  toolset_name:
    description: "Toolset description"
    tools:
      tool_name:
        description: "Tool description"
        execution:
          command: "command template with <<parameter>> placeholders"
        parameters:
          parameter_name:
            description: "Parameter description"
            required: true/false
```

### Top-level Tools Format (New)

This simpler format defines tools directly at the top level:

```yaml
tools:
  tool_name:
    description: "Tool description"
    execution:
      command: "command template with <<parameter>> placeholders"
    parameters:
      parameter_name:
        description: "Parameter description"
        required: true/false
```

### Combined Format

You can also use both formats in the same file:

```yaml
tools:
  echo:
    description: "Simple echo command"
    execution:
      command: "echo <<message>>"
    parameters:
      message:
        description: "Message to echo"
        required: true

toolsets:
  file:
    description: "File operations"
    tools:
      cat:
        description: "Display file contents"
        execution:
          command: "cat <<file_path>>"
        parameters:
          file_path:
            description: "Path to file"
            required: true
```

### Parameter Substitution

Parameters in command templates use the `<<parameter>>` syntax:

```yaml
command: "find . -name \"<<pattern>>\" -type f | xargs wc -l"
```

When the tool is invoked, these placeholders are replaced with the actual parameter values.

## 🔌 Claude Desktop Integration

### Using uvx (Recommended)

The simplest way to configure Claude Desktop is to use `npx` and `uvx` to install and run `mcp-this` on demand:

```json
{
  "mcpServers": {
    "mcp-this": {
      "command": "uvx",
      "args": [
        "mcp-this",
        // "--tools", "{\"tools\": <json string defining tools>}"
        "--tools-path", "/path/to/your/config.yaml"
      ],
    }
  }
}
```

This approach:
- Automatically installs the latest version from PyPI when needed
- Doesn't require manual installation or updates
- Cleanly isolates dependencies

### Using a locally installed package

If you've installed `mcp-this` globally or in your environment:

```json
{
  "mcpServers": {
    "mcp-this": {
      "command": "mcp-this",
      "args": ["--tools-path", "/path/to/your/config.yaml"],
    }
  }
}
```

## 🧪 Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-username/mcp-this.git
cd mcp-this

# Install dependencies
uv sync
```

### Development Commands

```bash
# Run linting
make linting

# Run tests
make tests

# Run the MCP server in development mode
make mcp_dev

# Build package
make package-build

# Publish package to PyPI
make package-publish
```

### Testing with MCP Inspector

```bash
# Test with MCP Inspector using environment variable
MCP_THIS_CONFIG_PATH=./path/to/config.yaml uv run mcp dev ./src/mcp_this/mcp_server.py

# Test with MCP Inspector using command-line flags
uv run mcp dev -m mcp_this --tools-path ./path/to/config.yaml

# Test with MCP Inspector using JSON string
uv run mcp dev -m mcp_this --tools '{"tools": {"example": {"description": "Example tool", "execution": {"command": "echo Test"}}}}'
```

## 📚 Examples

Check out the [examples](./examples) directory for sample configuration files and usage patterns:

- [top_level_tools_example.yaml](./examples/top_level_tools_example.yaml): Example of the simplified top-level tools format
- [toolset_example__curl.yaml](./examples/toolset_example__curl.yaml): Example of the original toolsets format

## 📜 License

This project is licensed under the terms of the LICENSE file included in the repository.
