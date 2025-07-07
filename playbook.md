# MCP-This Project Playbook

> **AI Coding Agent Note**: Keep this playbook updated as the project evolves. Update sections when new patterns, conventions, or architectural decisions are introduced.

---

## 1. Project Overview

**MCP-This** is a Python-based MCP (Model Control Protocol) Server that dynamically exposes CLI commands and AI prompt templates as tools through YAML configuration files. Instead of writing code, users define commands and prompts in YAML, and the server makes them available to MCP clients like Claude Desktop.

### Key Technologies & Frameworks
- **Python 3.11+** with modern type hints (`list[str]` style)
- **FastMCP** - MCP server framework for tool registration
- **uv** - Modern Python package manager and virtual environment management
- **YAML** - Configuration file format for tool and prompt definitions
- **Click** - Command-line interface framework
- **Ruff** - Fast Python linter and formatter
- **pytest** with asyncio support - Testing framework

### Architecture Patterns & Design Philosophy
- **Configuration-driven**: Tools and prompts defined in YAML, not code
- **Dynamic registration**: Runtime creation of MCP tools from configuration
- **Async-first**: All command execution is asynchronous
- **Template-based**: Command templates with placeholder substitution (`<<parameter>>`)
- **Handlebars-style prompts**: AI prompt templates with `{{argument}}` syntax
- **Validation-heavy**: Comprehensive configuration validation before registration
- **Dataclass modeling**: Structured data representation with `@dataclass`

---

## 2. Project Structure

```
/Users/shanekercheval/repos/mcp-this/
├── .github/workflows/          # GitHub Actions CI/CD
│   └── tests.yaml             # Test automation for Python 3.11-3.13
├── .gitignore                 # Git ignore patterns
├── .ruff.toml                 # Ruff linting and formatting configuration
├── LICENSE                    # Apache License 2.0
├── Makefile                   # Development workflow automation
├── README.md                  # Main project documentation
├── README_PRESETS.md          # Preset configurations documentation
├── documentation/             # Visual documentation assets
│   └── images/               # Screenshots and diagrams
├── examples/                  # Usage examples and demonstrations
│   ├── cli.py                # Example CLI usage
│   ├── custom_tools.yaml     # Custom tool configuration examples
│   ├── examples-*.ipynb      # Jupyter notebooks with examples
│   ├── mcp_config_cli.json   # MCP client configuration example
│   ├── prompts_example.yaml  # AI prompt template examples
│   ├── temp/                 # Temporary files for testing
│   └── tools_example.yaml    # Simple tool configuration examples
├── pyproject.toml            # Python project configuration, dependencies, build settings
├── src/mcp_this/             # Main source code
│   ├── __init__.py           # Package initialization, exports render_template
│   ├── __main__.py           # CLI entry point with argument parsing
│   ├── configs/              # Built-in preset configurations
│   │   ├── default.yaml      # Safe, read-only tools (file exploration, web scraping)
│   │   ├── editing.yaml      # File manipulation tools (create, edit, delete)
│   │   └── github.yaml       # GitHub integration tools and specialized prompts
│   ├── mcp_server.py         # Core MCP server implementation
│   ├── prompts.py            # Prompt parsing, validation, and registration
│   └── tools.py              # Tool parsing, command building, and execution
├── tests/                    # Comprehensive test suite
│   ├── fixtures/             # Test configuration files
│   │   ├── test_config.yaml
│   │   └── test_config_with_prompts.yaml
│   ├── test_*.py             # Test modules organized by component
└── uv.lock                   # UV lockfile for reproducible dependencies
```

### Directory Purposes

- **`src/mcp_this/`**: Main application code with clear separation of concerns
- **`src/mcp_this/configs/`**: Built-in YAML presets for different use cases
- **`tests/`**: Unit and integration tests with fixture-based configurations
- **`examples/`**: Working examples and demonstrations for users
- **`documentation/`**: Visual assets and additional documentation

### Important Configuration Files

- **`pyproject.toml`**: Project metadata, dependencies, build configuration, pytest settings
- **`.ruff.toml`**: Linting rules, line length (99), code quality standards
- **`uv.lock`**: Locked dependency versions for reproducible environments
- **`Makefile`**: Development commands and workflow automation

### File Naming Conventions

- **Test files**: `test_*.py` pattern in `tests/` directory
- **Configuration files**: `*.yaml` for tools/prompts, `*.json` for MCP client configs
- **Example files**: Descriptive names with `_example` suffix
- **Module files**: Snake_case matching functionality (e.g., `mcp_server.py`, `tools.py`)

### Organization Patterns

- **Preset configurations** belong in `src/mcp_this/configs/`
- **User examples** belong in `examples/`
- **Test fixtures** belong in `tests/fixtures/`
- **Documentation images** belong in `documentation/images/`

---

## 3. Getting Started

### Prerequisites
- **Python 3.11+** (required for modern type hints)
- **uv** package manager
- **System dependencies** for built-in tools:
  - `tree` - for directory tree generation
  - `lynx` - for web scraping functionality
  - `git` - for GitHub preset tools

### Environment Configuration

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and setup project**:
   ```bash
   git clone <repository-url>
   cd mcp-this
   uv sync  # Installs all dependencies including dev dependencies
   ```

3. **Install system dependencies** (Ubuntu/Debian):
   ```bash
   sudo apt-get update
   sudo apt-get install -y tree lynx git
   ```

---

## 4. Development Workflow

### Running the Project Locally

#### Development Mode with Built-in Presets
```bash
# Run with default preset (safe, read-only tools)
make mcp_dev

# Run with specific preset
MCP_THIS_CONFIG_PATH=./src/mcp_this/configs/editing.yaml make mcp_dev

# Run with custom configuration
make mcp_custom CONFIG=/path/to/your-config.yaml
```

#### Testing with uvx (Production-like)
```bash
# Test the package as end users would install it
make test-uvx
```

#### MCP Inspector for Tool Testing
```bash
# Test GitHub preset with MCP Inspector
make mcp_inspector_github
```

### Environment Variables

- **`MCP_THIS_CONFIG_PATH`**: Path to YAML configuration file
- **`UV_PUBLISH_TOKEN`**: PyPI publishing token (for releases)

### Dependency Management

```bash
# Add runtime dependency
make add-dep PKG=package_name

# Add development dependency  
make add-dev-dep PKG=package_name

# Sync dependencies after changes
uv sync
```

### Configuration Methods (Priority Order)

1. **CLI arguments**: `--config-path`, `--config-value`, `--preset`
2. **Environment variable**: `MCP_THIS_CONFIG_PATH`
3. **Default config**: `src/mcp_this/configs/default.yaml`

### Hot-Reload Capabilities

The MCP server supports development mode through `uv run mcp dev`, which provides:
- **Automatic restart** on code changes
- **Error reporting** with stack traces
- **Tool inspection** via MCP Inspector

---

## 5. Code Standards & Guidelines

### Language-Specific Conventions (Existing Patterns)

#### Type Hints Style
- **Modern syntax**: Use `list[str]`, `dict[str, any]` (not `List[str]`, `Dict`)
- **Union syntax**: Use `str | None` (not `Optional[str]`)
- **Comprehensive coverage**: All functions have type hints including return types

#### Naming Conventions

- **Functions/variables**: `snake_case` (e.g., `parse_tools`, `config_path`)
- **Classes**: `PascalCase` (e.g., `ToolInfo`, `PromptInfo`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `SAMPLE_CONFIG_PATH`)
- **File names**: `snake_case.py` (e.g., `mcp_server.py`)
- **YAML keys**: `kebab-case` for tool names (e.g., `get-directory-tree`)

#### Dataclass Usage Patterns
```python
@dataclass
class ToolInfo:
    """Information about a parsed tool from the configuration."""
    tool_name: str
    function_name: str
    command_template: str
    description: str
    parameters: dict[str, dict]
    param_string: str
    exec_code: str
    runtime_info: dict[str, any]
```

#### Async Function Patterns
```python
async def execute_command(cmd: str) -> str:
    """Execute a shell command asynchronously and return its output."""
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=None,
        )
        # ... rest of implementation
    except Exception as e:
        return f"Error: {e!s}"
```

### Error Handling Philosophy

#### Configuration Validation
- **Fail early**: Validate all configuration before registration
- **Specific errors**: Provide exact location and nature of validation failures
- **Helpful messages**: Include context and suggestions for fixes

#### Command Execution
- **Never crash**: Always return string results, even for errors
- **Detailed errors**: Include command that failed and error details
- **Stdout/stderr handling**: Prefer stdout, fall back to stderr for empty output

#### Exception Patterns
```python
try:
    # risky operation
    result = await operation()
except Exception as e:
    return f"Error: {e!s}"  # Use !s for clean string representation
```

### Documentation Standards

#### Docstring Style (Google Format)
```python
def build_command(command_template: str, parameters: dict[str, str]) -> str:
    r"""
    Build a shell command from a template by substituting parameter placeholders.

    Parameters are specified in the template using the format `<<parameter_name>>`.
    When a parameter value is provided, its placeholder is replaced with the value.

    Args:
        command_template: The command template with parameter placeholders.
            Example: "tail -n <<lines>> -f \"<<file>>\""
        parameters: Dictionary mapping parameter names to their values.
            Example: {"lines": 10, "file": "/var/log/syslog"}

    Returns:
        The processed command string with parameters substituted and cleaned up.
        Example: "tail -n 10 -f \"/var/log/syslog\""
    """
```

#### Module-Level Documentation
```python
#!/usr/bin/env python3
"""
MCP Server that dynamically creates command-line tools based on a YAML configuration file.

Each tool maps to a command-line command that can be executed by the server.
"""
```

---

## 6. Code Quality & Maintenance

### Testing Framework & Configuration

#### Pytest Configuration (pyproject.toml)
```toml
[tool.pytest.ini_options]
timeout = 60
timeout_method = "signal"
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

#### Test File Organization
- **Unit tests**: `test_*.py` in `tests/` directory
- **Component-based**: Separate test files for each major module
- **Fixture files**: Configuration examples in `tests/fixtures/`

#### Testing Patterns Used in Project

**Parametrized fixtures for multiple config methods**:
```python
@pytest.fixture(
    params=[
        pytest.param(("--config_path", str(SAMPLE_CONFIG_PATH)), id="config_path"),
        pytest.param(("--config_value", get_config_json()), id="config_value"),
    ],
)
def server_params(request: tuple) -> StdioServerParameters:
    """Create server parameters for different config methods."""
```

**Async test patterns**:
```python
@pytest.mark.asyncio
class TestMCPServer:
    """Test cases for the MCP server."""
    
    async def test_tool_execution(self, server_params):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Test tool functionality
```

#### Coverage Tools & Expectations
- **Coverage.py**: HTML reports generated in `htmlcov/`
- **Target coverage**: High coverage expected (current patterns suggest >90%)
- **Coverage commands**: `make coverage` and `make open_coverage`

### Linting Tools & Configuration

#### Ruff Configuration (.ruff.toml)
- **Line length**: 99 characters
- **Indent**: 4 spaces
- **Selected rules**: Comprehensive set including E, W, F, N, D, ANN, UP, PT, etc.
- **Ignored rules**: Specific exemptions for docs and test files

#### Code Formatting Standards
- **Automated formatting**: Ruff handles formatting automatically
- **Import organization**: Automatic import sorting and organization
- **Quote style**: Consistent quote usage enforced by Ruff

#### Pre-commit Integration
```bash
# Run linting with auto-fixes
make linting

# This runs:
uv run ruff check src --fix --unsafe-fixes
uv run ruff check tests --fix --unsafe-fixes
```

### Quality Check Commands
```bash
make tests         # Full test suite with linting and coverage
make unittests     # Unit tests only
make linting       # Linting only
make coverage      # Tests with coverage report
make verify        # All verification checks (linting + unittests + coverage)
```

### Build System & Dependency Management

#### UV Dependency Groups
- **Runtime dependencies**: Core packages (click, mcp, pyyaml, python-dotenv)
- **Development dependencies**: Testing, linting, and development tools

#### Build Commands
```bash
make package-build    # Build distribution packages
make package-publish  # Publish to PyPI (requires UV_PUBLISH_TOKEN)
make package         # Build and publish in one step
```

---

## 7. Project-Specific Guidelines

### YAML Configuration Patterns

#### Tool Definition Structure
```yaml
tools:
  tool-name:  # kebab-case naming
    description: |
      Multi-line description with examples and usage patterns.
      
      Examples:
        - tool_name(param="value") → expected output
        - tool_name(param="other") → other output
    execution:
      command: >-  # Use >- for multi-line commands, NOT |
        command template with <<parameter>> placeholders
    parameters:
      parameter:
        description: "Clear parameter description"
        required: true  # boolean, always explicit
```

#### Prompt Definition Structure  
```yaml
prompts:
  prompt-name:
    description: "Prompt description for LLM usage"
    template: |  # Use | for templates to preserve formatting
      Template with {{argument}} placeholders.
      {{#if optional_arg}}Conditional: {{optional_arg}}{{/if}}
    arguments:
      argument:
        description: "Argument description"
        required: true
```

### Command Template Patterns

#### Parameter Placeholder Rules
- **Syntax**: `<<parameter_name>>` for CLI parameters
- **Removal**: Empty parameters are completely removed from command
- **Quoting**: File paths automatically quoted in command templates
- **Multi-line**: Use `>-` to join lines with spaces, preserve structure

#### Template Examples from Codebase
```yaml
# Basic parameter substitution
command: "echo <<message>>"

# Optional parameters with fallback behavior
command: >-
  if [ "<<format>>" = "iso" ]; then 
    date -u +"%Y-%m-%dT%H:%M:%SZ"; 
  else 
    date "+%A, %B %d, %Y %I:%M %p"; 
  fi

# Complex multi-parameter commands with conditional logic
command: >-
  cd '<<directory>>' &&
  find . -type f <<arguments>>
  -not -path './.git/*'
  $(if [ -n "<<exclude_paths>>" ]; then echo "exclusions"; fi)
```

### Architecture Decision Rationale

#### Dynamic Function Generation
The project uses `exec()` to dynamically generate async functions for each tool. This pattern allows:
- **Runtime flexibility**: Tools defined at startup from configuration
- **Type safety**: Generated functions have proper signatures for MCP
- **Isolation**: Each tool function has its own namespace and runtime info

#### Separation of Concerns
- **`tools.py`**: CLI command parsing, execution, parameter handling
- **`prompts.py`**: AI prompt template parsing, validation, handlebars rendering  
- **`mcp_server.py`**: MCP integration, server lifecycle, configuration loading

#### Validation Strategy
- **Early validation**: All configuration validated before server starts
- **Specific errors**: Exact field and line information for debugging
- **Fail-safe defaults**: Server won't start with invalid configuration

### Integration Patterns Between Components

#### Configuration Flow
1. **Load**: YAML/JSON → Python dict (mcp_server.py)
2. **Validate**: Configuration structure and content (tools.py, prompts.py)
3. **Parse**: Extract ToolInfo/PromptInfo objects (tools.py, prompts.py)
4. **Generate**: Create executable functions (mcp_server.py)
5. **Register**: Add tools/prompts to MCP server (mcp_server.py)

#### Error Handling Chain
1. **Configuration errors**: Validation failures prevent server start
2. **Runtime errors**: Command execution errors returned as tool results
3. **MCP errors**: Server continues running, individual tools may fail

---

## 8. Command Reference

### Essential Commands

#### Setup & Environment
```bash
uv sync                    # Install all dependencies
make build                 # Alias for uv sync
```

#### Development
```bash
make mcp_dev              # Run MCP server with default config
make mcp_custom CONFIG=path  # Run with custom config
make mcp_inspector_github    # Test GitHub tools with inspector
```

#### Testing Commands
```bash
make tests                # Full test suite (linting + coverage)
make unittests           # Unit tests only (fast)
make linting             # Linting and formatting only
make coverage            # Tests with HTML coverage report
make open_coverage       # Open coverage report in browser
make verify              # All verification (linting + unittests + coverage)
```

### Package Management

#### Dependencies
```bash
make add-dep PKG=package_name      # Add runtime dependency
make add-dev-dep PKG=package_name  # Add development dependency
uv sync                            # Sync after dependency changes
```

#### Environment Management
```bash
uv venv                   # Create virtual environment
uv pip install -e .      # Editable install
uvx mcp-this             # Run package without installing
```

### Build & Quality

#### Package Building
```bash
make package-build       # Build wheel and source distributions
make package-publish     # Publish to PyPI (requires UV_PUBLISH_TOKEN)
make package            # Build and publish in sequence
```

#### Quality Checks
```bash
uv run ruff check src --fix        # Fix linting issues
uv run ruff check src --fix --unsafe-fixes  # Include unsafe fixes
uv run coverage run -m pytest      # Run tests with coverage
uv run coverage html               # Generate HTML coverage report
```

### Project-Specific Tools

#### MCP Testing & Installation
```bash
make mcp_install         # Install in Claude Desktop (default config)
make mcp_install_custom CONFIG=path  # Install with custom config
make test-uvx           # Test package via uvx (production-like)
```

#### Development Tools
```bash
make chat               # Interactive chat CLI with MCP tools
make chat_tools         # Show available MCP tools
```

#### Example Usage
```bash
# Run examples
uv run python examples/cli.py -chat --mcp_config examples/mcp_config_cli.json --model 'gpt-4o'
uv run python examples/cli.py -tools --mcp_config examples/mcp_config_cli.json
```

---

## 9. Safety Guidelines

### ⚠️ NEVER DO

#### Version Control Operations
- **No git operations**: Never run `git commit`, `git push`, `git merge`, or branch operations
- **No remote changes**: Never push to repositories or modify remote branches
- **No git configuration**: Never modify `.gitignore`, `.gitattributes`, or git settings

#### Destructive File Operations  
- **No recursive deletion**: Never use `rm -rf` or equivalent destructive commands
- **No system file modification**: Never modify system files, `/etc/`, or OS configurations
- **No permission changes**: Never use `chmod`, `chown`, or modify file permissions
- **No disk operations**: Never format drives or modify partition tables

#### External Service Calls
- **No production APIs**: Never call production APIs or live services during development
- **No deployments**: Never deploy to production, staging, or cloud environments
- **No publishing**: Never publish packages to PyPI or other registries without explicit approval
- **No CI/CD triggers**: Never manually trigger deployment pipelines or release workflows

#### System-Level Changes
- **No global installs**: Never install packages globally or modify system Python
- **No environment modifications**: Never modify PATH, shell configuration, or system variables
- **No service management**: Never start/stop system services or modify daemon configurations
- **No network configuration**: Never modify firewall rules, DNS, or network settings

#### Cost-Incurring Operations
- **No cloud resources**: Never create cloud instances, databases, or paid services
- **No paid API calls**: Never make calls to paid APIs or services that incur charges
- **No resource scaling**: Never modify cloud resource limits or scaling configurations
- **No billing changes**: Never modify payment methods or billing configurations

### Safe Development Practices

#### Recommended Workflow
1. **Use virtual environments**: Always work within `uv sync` created environments
2. **Test locally first**: Use `make tests` before any changes
3. **Validate configurations**: Test YAML configs with built-in validation
4. **Use development modes**: Prefer `make mcp_dev` for testing
5. **Check examples**: Reference `examples/` directory for usage patterns

#### Configuration Safety
- **Validate YAML**: Always test configurations with `uv run python -m mcp_this --config-path config.yaml`
- **Test tools safely**: Use read-only operations first, then progressively test write operations
- **Review command templates**: Ensure shell commands are safe and properly quoted
- **Check parameter validation**: Verify required/optional parameter handling

---

*This playbook should be maintained and updated as the project evolves. When new patterns, architectural decisions, or conventions are established, update the relevant sections to keep this guide current and useful for AI coding agents and human developers.*