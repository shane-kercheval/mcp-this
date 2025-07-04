# `mcp-this`

> An MCP Server that dynamically exposes CLI/bash commands as tools through YAML configuration files.

`mcp-this` lets you turn any command-line tool into an MCP tool that Claude can use. Instead of writing code, you simply define commands and their parameters in YAML files, and the server makes them available to MCP clients like Claude Desktop.

**Core Value:** Transform any CLI command into an MCP tool using simple YAML configuration.

---

## How It Works

Define tools in YAML:

```yaml
tools:
  get-current-time:
    description: |
      Display the current date and time in various formats.
      
      Examples:
      - get_current_time(format="iso") → 2025-05-18T17:17:39Z
      - get_current_time(format="readable") → Friday, May 18, 2025 5:17 PM
    execution:
      command: >-
        if [ "<<format>>" = "iso" ]; then 
          date -u +"%Y-%m-%dT%H:%M:%SZ"; 
        elif [ "<<format>>" = "readable" ]; then 
          date "+%A, %B %d, %Y %I:%M %p"; 
        else 
          echo "ISO: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"; 
          echo "Readable: $(date "+%A, %B %d, %Y %I:%M %p")"; 
        fi
    parameters:
      format:
        description: "Time format: iso, readable, or empty for both"
        required: false

  system-info:
    description: Get basic system information
    execution:
      command: uname -a && echo "CPU: $(nproc) cores"
    parameters: {}
```

Use in Claude Desktop:

```json
{
  "mcpServers": {
    "mcp-this-custom": {
      "command": "uvx",
      "args": ["mcp-this", "--config-path", "/path/to/your-tools.yaml"]
    }
  }
}
```

That's it! Claude can now use your custom CLI tools.

---

## Quick Start

### 1. Install uvx
```bash
# Install uv (includes uvx)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Create Your First Tool

Create `my-tools.yaml`:

```yaml
tools:
  web-scraper:
    description: Fetch a webpage and convert it to clean, readable text
    execution:
      command: curl -s '<<url>>' | lynx -dump -stdin
    parameters:
      url:
        description: URL of the webpage to fetch
        required: true

  find-large-files:
    description: Find files larger than specified size in a directory
    execution:
      command: find '<<directory>>' -type f -size +<<size>> -exec ls -lh {} \;
    parameters:
      directory:
        description: Directory to search
        required: true
      size:
        description: Minimum file size (e.g., 100M, 1G)
        required: true
```

### 3. Configure Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "uvx",
      "args": ["mcp-this", "--config-path", "/path/to/my-tools.yaml"]
    }
  }
}
```

### 4. Restart Claude Desktop

Your tools are now available! Claude can fetch web content and find large files using your custom commands.

---

## Configuration Format

### Tool Definition

```yaml
tools:
  tool-name:
    description: "Description with usage examples"
    execution:
      command: "command-template <<parameter1>> <<optional_param>>"
    parameters:
      parameter1:
        description: "Parameter description"
        required: true
      optional_param:
        description: "Optional parameter description"  
        required: false
```

**Key Points:**
- Use `<<parameter>>` placeholders in commands
- Parameters marked `required: false` are removed from commands if not provided
- Use `command: >-` for multi-line commands (not `command: |`)

### Prompt Definition

```yaml
prompts:
  prompt-name:
    description: "Prompt description"
    template: |
      Template with {{argument}} placeholders.
      {{#if optional_arg}}Conditional: {{optional_arg}}{{/if}}
    arguments:
      argument:
        description: "Argument description"
        required: true
      optional_arg:
        description: "Optional argument"
        required: false
```

**Prompts vs Tools:**
- **Tools** execute commands and use `<<parameter>>` syntax
- **Prompts** generate text templates and use `{{argument}}` syntax with Handlebars

---

## Configuration Methods

| Method | Usage | Example |
|--------|--------|---------|
| **YAML File** | `--config-path <path>` | `--config-path ./my-tools.yaml` |
| **JSON String** | `--config-value <json>` | `--config-value '{"tools":{...}}'` |
| **Environment Variable** | `MCP_THIS_CONFIG_PATH` | `export MCP_THIS_CONFIG_PATH=./tools.yaml` |
| **Built-in Preset** | `--preset <n>` | `--preset default` |

## Pre-Built Tool Collections (Presets)

For convenience, `mcp-this` includes ready-to-use tool collections:

- **`default`** - Safe, read-only tools (file exploration, web scraping)
- **`editing`** - File manipulation tools (create, edit, delete)  
- **`github`** - GitHub integration tools (PR analysis, repository operations)

**Quick usage:**
```json
{
  "mcpServers": {
    "mcp-this": {
      "command": "uvx", 
      "args": ["mcp-this", "--preset", "default"]
    }
  }
}
```

> **See [README_PRESETS.md](README_PRESETS.md) for complete preset documentation, tool lists, dependencies, and advanced setup.**

---

## Real-World Examples

### Development Workflow Tools

```yaml
tools:
  git-status-summary:
    description: Get a concise overview of git repository status
    execution:
      command: >-
        echo "=== Branch ===" && git branch --show-current &&
        echo "=== Status ===" && git status --porcelain &&
        echo "=== Recent Commits ===" && git log --oneline -5
    parameters: {}

  test-runner:
    description: Run tests with optional pattern matching
    execution:
      command: >-
        if [ -n "<<pattern>>" ]; then
          npm test -- --grep "<<pattern>>"
        else
          npm test
        fi
    parameters:
      pattern:
        description: Test pattern to match (optional)
        required: false

  docker-container-logs:
    description: Get logs from a Docker container
    execution:
      command: docker logs <<container_name>> --tail <<lines>>
    parameters:
      container_name:
        description: Name or ID of the Docker container
        required: true
      lines:
        description: Number of log lines to show (default 100)
        required: false
        default: "100"
```

### System Administration Tools

```yaml
tools:
  port-checker:
    description: Check what process is using a specific port
    execution:
      command: lsof -i :<<port>>
    parameters:
      port:
        description: Port number to check
        required: true

  service-status:
    description: Check the status of a system service
    execution:
      command: systemctl status <<service_name>>
    parameters:
      service_name:
        description: Name of the service to check
        required: true

  disk-usage-analyzer:
    description: Analyze disk usage and find largest directories
    execution:
      command: >-
        echo "=== Disk Usage Summary ===" &&
        df -h <<path>> &&
        echo "=== Largest Directories ===" &&
        du -h <<path>> | sort -hr | head -10
    parameters:
      path:
        description: Path to analyze (default current directory)
        required: false
        default: "."
```

---

## Python API Usage

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Using custom configuration
server_params = StdioServerParameters(
    command='uvx',
    args=['mcp-this', '--config-path', '/path/to/tools.yaml'],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # List available tools
        tools = await session.list_tools()
        print([tool.name for tool in tools.tools])
        
        # Use a tool
        result = await session.call_tool(
            'git-status-summary',
            {}
        )
        print(result.content[0].text)
```

---

## Installation Options

### Via uvx (Recommended)
```bash
# No installation needed - uvx runs tools in isolated environments
uvx mcp-this --config-path ./my-tools.yaml
```

### Via pip
```bash
pip install mcp-this
mcp-this --config-path ./my-tools.yaml
```

### From Source
```bash
git clone https://github.com/your-username/mcp-this.git
cd mcp-this
uv sync
python -m mcp_this --config-path ./my-tools.yaml
```

---

## Security Considerations

⚠️ **Important:** `mcp-this` executes shell commands based on your configuration. Always:

- **Use trusted configuration files only**
- **Validate user inputs in production environments**
- **Run with minimal necessary privileges**
- **Consider containerization for additional security**
- **Review commands for dangerous operations**

See the [Security section](README_PRESETS.md#security-considerations) for detailed security guidance.

---

## Development

### Setup
```bash
git clone https://github.com/your-username/mcp-this.git
cd mcp-this
uv sync
```

### Testing
```bash
make tests         # Run all tests
make unittests     # Unit tests only
make linting       # Linting only
make open_coverage # View coverage report
```

### Building
```bash
make package-build    # Build package
make package-publish  # Publish (requires UV_PUBLISH_TOKEN)
```

---

## License

[Apache License 2.0](LICENSE)