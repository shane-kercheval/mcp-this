# Built-in Tool Presets

This document covers the pre-built tool collections (presets) included with `mcp-this`. For creating custom tools, see the main [README.md](README.md).

## Overview

Presets are pre-configured YAML files located in `src/mcp_this/configs/` that provide ready-to-use tool collections for common workflows. They're designed to get you started quickly without writing custom configurations.

**Available Presets:**
- **`default`** - Safe, read-only tools for analysis and exploration
- **`editing`** - File and directory manipulation tools  
- **`github`** - GitHub integration and repository analysis tools

---

## Default Preset

**Purpose:** Safe, read-only tools for file analysis, exploration, and information gathering  
**Best for:** General development, content analysis, system exploration  
**Safety:** ✅ Read-only operations, no file modifications

### Usage

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

Or explicitly:
```json
{
  "mcpServers": {
    "mcp-this-default": {
      "command": "uvx", 
      "args": ["mcp-this", "--preset", "default"]
    }
  }
}
```

### Available Tools

| Tool | Description | Example Use Cases |
|------|-------------|-------------------|
| **get-directory-tree** | Generate directory trees with gitignore support and exclusions | Understand project structure, documentation |
| **find-files** | Locate files by name, pattern, type, size, date, or other criteria | Find configuration files, locate large files |
| **find-text-patterns** | Search for text patterns in files with context and filtering | Find TODO comments, search for API keys |
| **extract-file-text** | Display file contents with options for line numbers and filtering | View specific file sections, extract code snippets |
| **extract-code-info** | Analyze code files to extract functions, classes, imports, and TODOs | Code review, architecture analysis |
| **web-scraper** | Fetch webpages and convert to clean, readable text using lynx | Research, content analysis, competitor analysis |

### Dependencies

**macOS:**
```bash
brew install tree lynx
```

**Ubuntu/Debian:**
```bash
sudo apt install tree lynx
```

**Windows:**
- Install `tree` via package manager or use built-in `tree` command
- Install `lynx` via WSL or Windows package managers

### Tool Examples

**Directory Analysis:**
```yaml
# Get project structure
get-directory-tree:
  directory: "/path/to/project"
  custom_excludes: "|build|dist|coverage"
  format_args: "-L 3 --dirsfirst"

# Find large files
find-files:
  directory: "/path/to/project"  
  arguments: "-size +10M -not -path */node_modules/*"
```

**Content Search:**
```yaml
# Find configuration files
find-text-patterns:
  directory: "/path/to/project"
  pattern: "api.*key|secret|password"
  context_lines: 2
  file_pattern: "*.yml,*.yaml,*.json,*.env"

# Extract specific functions
extract-code-info:
  file_path: "/path/to/file.py"
  extract_functions: true
  extract_classes: true
```

---

## Editing Preset

**Purpose:** File and directory manipulation for development workflows  
**Best for:** Content creation, file management, development tasks  
**Safety:** ⚠️ **ALPHA** - Can modify/delete files, use with caution

### Usage

```json
{
  "mcpServers": {
    "mcp-this-editing": {
      "command": "uvx",
      "args": ["mcp-this", "--preset", "editing"]
    }
  }
}
```

### Available Tools

| Tool | Description | Capabilities |
|------|-------------|--------------|
| **create-file** | Create new files with specified content | Create scripts, configs, documentation |
| **edit-file** | Modify existing files with precise control | Insert, replace, delete specific lines |
| **create-directory** | Create directories and nested directory structures | Project setup, organizing file structure |

### Safety Notes

- **⚠️ ALPHA STATUS:** These tools are in early development
- **File Overwriting:** `create-file` will overwrite existing files without warning
- **Backup Recommended:** Always backup important files before using editing tools
- **Version Control:** Use in version-controlled directories when possible

### Tool Examples

**File Creation:**
```yaml
# Create a new Python script
create-file:
  path: "/path/to/script.py"
  content: |
    #!/usr/bin/env python3
    """
    New Python script
    """
    
    def main():
        print("Hello, World!")
    
    if __name__ == "__main__":
        main()

# Create configuration file
create-file:
  path: "/path/to/config.yaml"
  content: |
    app:
      name: "My App"
      version: "1.0.0"
      debug: false
```

**File Editing:**
```yaml
# Insert new function
edit-file:
  path: "/path/to/module.py"
  operation: "insert"
  line_number: 10
  content: |
    def new_function():
        """New functionality"""
        return True

# Replace configuration section  
edit-file:
  path: "/path/to/config.ini"
  operation: "replace"
  start_line: 5
  end_line: 8
  content: |
    [database]
    host = localhost
    port = 5432
    name = myapp
```

---

## GitHub Preset

**Purpose:** GitHub integration, PR analysis, and repository operations  
**Best for:** Code review, pull request analysis, repository management  
**Dependencies:** GitHub CLI (`gh`) with authentication

### Usage

```json
{
  "mcpServers": {
    "mcp-this-github": {
      "command": "uvx",
      "args": ["mcp-this", "--preset", "github"]
    }
  }
}
```

### Setup Requirements

**1. Install GitHub CLI:**

macOS:
```bash
brew install gh
```

Ubuntu/Debian:
```bash
sudo apt install gh
```

Windows:
```bash
winget install GitHub.cli
```

**2. Authenticate:**
```bash
gh auth login
```

Follow the prompts to authenticate with your GitHub account.

### Available Tools

| Tool | Description | Use Cases |
|------|-------------|-----------|
| **get-github-pull-request-info** | Comprehensive PR analysis with overview, files changed, and complete diff | Code review, understanding changes, PR summaries |
| **get-local-git-changes-info** | Analyze local Git changes with status, diffs, and untracked files | Pre-commit review, change summarization |

### Available Prompts

| Prompt | Description | Use Cases |
|--------|-------------|-----------|
| **create-pr-description** | Generate comprehensive pull request descriptions from code changes | PR creation, change documentation |
| **code-review** | Perform thorough code reviews with best practices focus | Quality assurance, security review, mentoring |

### Tool Examples

**PR Analysis:**
```yaml
# Analyze a GitHub PR
get-github-pull-request-info:
  pr_url: "https://github.com/owner/repo/pull/123"

# Analyze local changes before committing
get-local-git-changes-info:
  directory: "/path/to/repository"
```

### Prompt Usage in Claude Desktop

**Using Prompts:**
1. Click the `+` icon in Claude Desktop's message input
2. Select "Add from mcp-this-github"  
3. Choose your prompt:
   - **create-pr-description** - For generating PR descriptions
   - **code-review** - For conducting code reviews

**Prompt Inputs:**
- GitHub PR URLs (tools will fetch automatically)
- Code snippets or diffs
- Local directory paths for analysis
- Individual file paths

**Example Workflow:**
1. Make local changes to your repository
2. Use `get-local-git-changes-info` to analyze changes
3. Use `create-pr-description` prompt with the output
4. Use `code-review` prompt to review before submitting

---

## Advanced Preset Usage

### Multiple Presets

Run multiple presets simultaneously for comprehensive functionality:

```json
{
  "mcpServers": {
    "mcp-this-default": {
      "command": "uvx",
      "args": ["mcp-this", "--preset", "default"]
    },
    "mcp-this-editing": {
      "command": "uvx", 
      "args": ["mcp-this", "--preset", "editing"]
    },
    "mcp-this-github": {
      "command": "uvx",
      "args": ["mcp-this", "--preset", "github"]
    }
  }
}
```

### Combining Presets with Custom Tools

```json
{
  "mcpServers": {
    "mcp-this-default": {
      "command": "uvx",
      "args": ["mcp-this", "--preset", "default"]
    },
    "mcp-this-custom": {
      "command": "uvx",
      "args": ["mcp-this", "--config-path", "/path/to/custom-tools.yaml"]
    }
  }
}
```

### Environment-Specific Configurations

**Development:**
```json
{
  "mcpServers": {
    "mcp-this-dev": {
      "command": "uvx",
      "args": ["mcp-this", "--preset", "editing"]
    }
  }
}
```

**Production/Safe:**
```json
{
  "mcpServers": {
    "mcp-this-safe": {
      "command": "uvx", 
      "args": ["mcp-this", "--preset", "default"]
    }
  }
}
```

---

## Troubleshooting

### Common Issues

**"spawn uvx: ENOENT" Error:**
- Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Ensure `uvx` is in PATH or use full path
- On some systems: `/Users/<username>/.local/bin/uvx`

**Missing Dependencies:**
- Default preset: Install `tree` and `lynx`
- GitHub preset: Install and authenticate `gh`
- Check specific tool requirements above

**Tools Not Appearing:**
- Restart Claude Desktop after configuration changes
- Check JSON syntax in `claude_desktop_config.json`
- Verify file paths are correct and accessible

**Permission Errors:**
- Ensure MCP server has read access to config files
- For editing preset, ensure write permissions to target directories
- Run with appropriate user permissions

### Debugging

**Test Configuration:**
```bash
# Test preset loading
uvx mcp-this --preset default --help

# Test custom config  
uvx mcp-this --config-path ./my-tools.yaml --help

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('my-tools.yaml'))"
```

**Verbose Output:**
```bash
uvx mcp-this --preset default --verbose
```

---

## Security Considerations

### Risk Assessment by Preset

**Default Preset:** ✅ **Low Risk**
- Read-only operations
- No file modifications
- Safe for production environments
- Web scraping uses external commands (lynx)

**Editing Preset:** ⚠️ **High Risk**  
- Can create, modify, and delete files
- Potential for data loss
- Requires careful parameter validation
- Recommended for development environments only

**GitHub Preset:** 🔶 **Medium Risk**
- Reads repository data
- Requires GitHub authentication
- Network operations to GitHub API
- Read-only GitHub operations

### General Security Guidelines

**Configuration Security:**
- Use trusted configuration files only
- Validate YAML/JSON configurations before use
- Store sensitive configurations securely
- Avoid hardcoded secrets in configurations

**Runtime Security:**
- Run with minimal necessary privileges
- Use dedicated user accounts for MCP servers
- Consider containerization for isolation
- Monitor command execution and resource usage

**Development vs Production:**
- Use `default` preset for production/shared environments
- Reserve `editing` preset for development environments
- Implement additional access controls as needed
- Regular security audits of custom configurations

**Input Validation:**
- Sanitize user inputs in production
- Implement parameter validation
- Use allowlists for sensitive parameters
- Log and monitor tool usage

### Recommended Security Setup

**Development Environment:**
```json
{
  "mcpServers": {
    "mcp-this-dev": {
      "command": "uvx",
      "args": ["mcp-this", "--preset", "editing"],
      "env": {
        "USER": "developer"
      }
    }
  }
}
```

**Production Environment:**
```json
{
  "mcpServers": {
    "mcp-this-prod": {
      "command": "uvx", 
      "args": ["mcp-this", "--preset", "default"],
      "env": {
        "USER": "readonly"
      }
    }
  }
}
```

---

## Preset Configuration Files

The preset configurations are stored in `src/mcp_this/configs/`:

- **`default.yaml`** - Default preset tools
- **`editing.yaml`** - Editing preset tools  
- **`github.yaml`** - GitHub preset tools and prompts

These files serve as examples for creating custom configurations. You can view them in the repository to understand the structure and create similar custom tool definitions.