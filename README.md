# `mcp-this`

> An MCP Server that dynamically exposes CLI/bash commands as tools and prompt templates through YAML configuration files.

`mcp-this` lets you turn any command-line tool into an MCP tool and create structured prompt templates that any MCP Client (e.g. Claude Desktop) can use. Instead of writing code, you simply define commands, prompts, and their parameters in YAML files, and the MCP Server makes them available to MCP Clients like Claude Desktop.

**Core Value:** Transform CLI commands into MCP tools and create reusable prompt templates using simple YAML configuration.

---

## How It Works

Define **tools** (CLI commands) and **prompts** (AI templates) in YAML:

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

prompts:
  code-reviewer:
    description: Perform a thorough code review with best practices focus
    template: |
      Please review the following code with a focus on:
      - Code quality and best practices
      - Security vulnerabilities
      - Performance considerations
      {{#if focus_area}}- Special attention to: {{focus_area}}{{/if}}
      
      Code to review:
      {{code}}
      
      {{#if context}}Additional context: {{context}}{{/if}}
    arguments:
      code:
        description: Code to review
        required: true
      focus_area:
        description: Specific area to focus on (e.g., security, performance)
        required: false
      context:
        description: Additional context about the code
        required: false
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

That's it! Claude can now:
- **Execute your custom CLI tools** (get-current-time, system-info)
- **Use your structured prompt templates** (code-reviewer with guided arguments)

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

### 2.1. Add AI Prompt Templates (Optional)

Enhance your `my-tools.yaml` with structured prompt templates:

```yaml
tools:
  # ... your tools above ...

prompts:
  summarize-webpage:
    description: Generate a structured summary of webpage content
    template: |
      Please analyze the following webpage content and provide:
      
      1. **Main Topic**: What is this page about?
      2. **Key Points**: {{num_points}} most important points
      3. **Target Audience**: Who is this content for?
      {{#if focus}}4. **{{focus}} Analysis**: Specific insights about {{focus}}{{/if}}
      
      Content:
      {{content}}
    arguments:
      content:
        description: Webpage content to summarize
        required: true
      num_points:
        description: Number of key points to extract (default 5)
        required: false
      focus:
        description: Specific aspect to focus on (e.g., technical, business, educational)
        required: false

  file-analysis:
    description: Analyze files for specific purposes
    template: |
      Analyze the following files for {{analysis_type}}:
      
      {{#if criteria}}Focus on: {{criteria}}{{/if}}
      
      {{files}}
      
      Please provide:
      - Summary of findings
      - Recommendations
      - {{#if format}}Output in {{format}} format{{/if}}
    arguments:
      files:
        description: File contents or paths to analyze
        required: true
      analysis_type:
        description: Type of analysis (security, performance, quality, etc.)
        required: true
      criteria:
        description: Specific criteria or standards to check against
        required: false
      format:
        description: Output format (markdown, JSON, report, etc.)
        required: false
```

**Using Prompts in Claude Desktop:**
1. Click the `+` icon in the message input
2. Select "Add from mcp-this-custom"
3. Choose your prompt (e.g., "summarize-webpage")
4. Fill in the arguments - Claude will guide you through the required and optional fields

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

Your tools and prompts are now available! Claude can:
- **Fetch web content and find large files** using your custom CLI tools
- **Use structured prompt templates** for guided analysis and summarization

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

## Pre-Built Tool & Prompt Collections (Presets)

For convenience, `mcp-this` includes ready-to-use collections of tools and prompts:

- **`default`** - Safe, read-only tools (file exploration, web scraping)
- **`editing`** - File manipulation tools (create, edit, delete)  
- **`github`** - GitHub integration tools (PR analysis, repository operations) + specialized prompts (code-review, create-pr-description)

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

### AI-Powered Workflow Prompts

```yaml
prompts:
  refactor-code:
    description: Guide code refactoring with specific goals and constraints
    template: |
      Please refactor the following code with these objectives:
      {{#if goals}}
      **Goals:**
      {{goals}}
      {{/if}}
      
      **Constraints:**
      - Maintain existing functionality
      - {{#if language}}Follow {{language}} best practices{{/if}}
      - {{#if performance}}Optimize for {{performance}}{{/if}}
      {{#if additional_constraints}}
      - {{additional_constraints}}
      {{/if}}
      
      **Code to refactor:**
      ```
      {{code}}
      ```
      
      Please provide:
      1. Refactored code with explanations
      2. Summary of changes made
      3. Potential risks or considerations
    arguments:
      code:
        description: Code to refactor
        required: true
      goals:
        description: Specific refactoring goals (e.g., improve readability, reduce complexity)
        required: false
      language:
        description: Programming language for best practices
        required: false
      performance:
        description: Performance optimization target (speed, memory, etc.)
        required: false
      additional_constraints:
        description: Any additional constraints or requirements
        required: false

  technical-documentation:
    description: Generate comprehensive technical documentation
    template: |
      Create {{doc_type}} documentation for:
      
      {{content}}
      
      **Requirements:**
      - Target audience: {{audience}}
      {{#if style}}- Documentation style: {{style}}{{/if}}
      {{#if sections}}- Include sections: {{sections}}{{/if}}
      - {{#if detail_level}}Detail level: {{detail_level}}{{/if}}
      
      {{#if examples}}**Include examples:** {{examples}}{{/if}}
      
      Please structure the documentation with clear headings, examples, and actionable information.
    arguments:
      content:
        description: Code, API, or system to document
        required: true
      doc_type:
        description: Type of documentation (API, user guide, technical spec, etc.)
        required: true
      audience:
        description: Target audience (developers, end-users, administrators, etc.)
        required: true
      style:
        description: Documentation style (formal, conversational, tutorial, reference)
        required: false
      sections:
        description: Specific sections to include
        required: false
      detail_level:
        description: Level of detail (high-level, detailed, comprehensive)
        required: false
      examples:
        description: Types of examples to include
        required: false
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