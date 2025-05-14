# MCP-This

> MCP Server that exposes CLI commands as tools for Claude using YAML configuration files

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
# Using config file path
mcp-this --config /path/to/your/config.yaml

# Using environment variable
export MCP_THIS_CONFIG_PATH=/path/to/your/config.yaml
mcp-this
```

## 🛠️ Configuration Structure

The configuration YAML files follow this structure:

```yaml
toolsets:
  toolset_name:
    description: "Toolset description"
    tools:
      tool_name:
        description: "Tool description"
        help_text: "Detailed help text for the tool"
        execution:
          command: "command template with <<parameter>> placeholders"
          uses_working_dir: true/false
        parameters:
          parameter_name:
            description: "Parameter description"
            required: true/false
```

### Parameter Substitution

Parameters in command templates use the `<<parameter>>` syntax:

```yaml
command: "find . -name \"<<pattern>>\" -type f | xargs wc -l"
```

When the tool is invoked, these placeholders are replaced with the actual parameter values.

## 🔌 Claude Desktop Integration

### Using npx and uvx (Recommended)

The simplest way to configure Claude Desktop is to use `npx` and `uvx` to install and run `mcp-this` on demand:

```json
{
  "mcpServers": {
    "mcp-this": {
      "command": "npx",
      "args": [
        "-y",
        "uvx",
        "mcp-this",
        "--config",
        "/path/to/your/config.yaml"
      ],
      "env": {
        "SOME_API_KEY": "your-secret-key"
      }
    }
  }
}
```

This approach:
- Automatically installs the latest version from PyPI when needed
- Doesn't require manual installation or updates
- Cleanly isolates dependencies

### Using the default configuration

If you want to use the default configuration that comes with the package:

```json
{
  "mcpServers": {
    "mcp-this": {
      "command": "npx",
      "args": [
        "-y",
        "uvx",
        "mcp-this"
      ]
    }
  }
}
```

### Using a locally installed package

If you've installed `mcp-this` globally or in your environment:

```json
{
  "mcpServers": {
    "mcp-this": {
      "command": "mcp-this",
      "args": ["--config", "/path/to/your/config.yaml"],
      "env": {
        "SOME_API_KEY": "your-secret-key"
      }
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
# Test with MCP Inspector
MCP_THIS_CONFIG_PATH=./path/to/config.yaml uv run mcp dev ./src/mcp_this/mcp_server.py
```

## 📚 Examples

Check out the [examples](./examples) directory for sample configuration files and usage patterns.

## 📜 License

This project is licensed under the terms of the LICENSE file included in the repository.