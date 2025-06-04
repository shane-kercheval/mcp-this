#!/usr/bin/env python3
"""
MCP Server that dynamically creates command-line tools based on a YAML configuration file.

Each tool maps to a command-line command that can be executed by the server.
"""
import os
import yaml
import json
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import sys
from collections.abc import Callable
from mcp_this.tools import ToolInfo, build_command, execute_command, parse_tools
from mcp_this.prompts import PromptInfo, parse_prompts


mcp = FastMCP("Dynamic CLI Tools")


def render_template(template: str, kwargs: dict) -> str:
    """
    Render a template with variable substitution and conditional blocks.

    Supports:
    - {{variable}} - Simple variable substitution
    - {{#if variable}}content{{/if}} - Conditional blocks
    - {{#if variable}}content{{else}}fallback{{/if}} - Conditional blocks with else
    """
    # Simple template rendering - replace {{variable}} with values
    for arg_name, arg_value in kwargs.items():
        if arg_value:  # Only replace if value is provided
            template = template.replace("{{" + arg_name + "}}", str(arg_value))

    # Process {{#if variable}}content{{else}}fallback{{/if}} blocks
    def handle_if_block(match: re.Match) -> str:
        var_name = match.group(1)
        if_content = match.group(2)
        else_content = match.group(3) if match.group(3) else ""
        # Include if_content if variable exists and is not empty, else else_content
        if kwargs.get(var_name):
            return if_content
        return else_content

    # Replace {{#if variable}}content{{else}}fallback{{/if}} blocks (optional else)
    template = re.sub(
        r'\{\{#if (\w+)\}\}(.*?)(?:\{\{else\}\}(.*?))?\{\{/if\}\}',
        handle_if_block,
        template,
        flags=re.DOTALL,
    )
    # Clean up any remaining unfilled variables
    template = re.sub(r'\{\{\w+\}\}', '', template)
    return template.strip()


def get_default_config_path() -> Path | None:
    """Get the path to the default configuration file."""
    # Look for default config in package directory
    package_dir = Path(__file__).parent
    # Correct path where the file is stored
    default_config = package_dir / "configs" / "default.yaml"
    if default_config.exists():
        return default_config
    return None


def load_config(config_path: str | None = None, tools: str | None = None) -> dict:
    """
    Load configuration from a YAML file or JSON string.

    Args:
        config_path: Path to the YAML configuration file.
                    If None and tools is None, use MCP_THIS_CONFIG_PATH environment variable
                    or default config.
        tools: JSON-structured configuration string.
                    Takes precedence over config_path if both are provided.

    Returns:
        The loaded configuration dictionary.

    Raises:
        ValueError: If no configuration source is provided.
        FileNotFoundError: If the configuration file does not exist.
        JSONDecodeError: If the JSON configuration string is invalid.
    """
    # Priority: tools > config_path > env var > default config
    if tools:
        try:
            config = json.loads(tools)
            if not config:
                raise ValueError("Configuration value is empty")
            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON configuration: {e}")

    if not config_path:
        config_path = os.environ.get("MCP_THIS_CONFIG_PATH")

    if not config_path:
        # Try to use default config
        default_path = get_default_config_path()
        if default_path:
            config_path = str(default_path)
        else:
            raise ValueError(
                "No configuration provided. Please provide --config_path, --config_value, "
                "set MCP_THIS_CONFIG_PATH environment variable, "
                "or include a default configuration in the package.",
            )

    config_path_obj = Path(config_path)
    if not config_path_obj.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load configuration
    try:
        with open(config_path_obj) as f:
            config = yaml.safe_load(f)
            if not config:
                raise ValueError("Configuration file is empty")
            return config
    except Exception as e:
        raise ValueError(f"Error loading configuration: {e}")


def validate_config(config: dict) -> None:
    """
    Validate configuration.

    Args:
        config: The configuration dictionary.

    Raises:
        ValueError: If the configuration is invalid.
    """
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")

    # Check if we have at least a tools or prompts section
    if 'tools' not in config and 'prompts' not in config:
        raise ValueError("Configuration must contain a 'tools' and/or 'prompts' section")

    # Validate tools section if present
    if 'tools' in config:
        if not isinstance(config['tools'], dict):
            raise ValueError("'tools' must be a dictionary")

        for tool_name, tool_config in config['tools'].items():
            validate_tool_config(tool_name, tool_config)

    # Validate prompts section if present
    if 'prompts' in config:
        from mcp_this.prompts import validate_prompt_config
        if not isinstance(config['prompts'], dict):
            raise ValueError("'prompts' must be a dictionary")

        for prompt_name, prompt_config in config['prompts'].items():
            validate_prompt_config(prompt_name, prompt_config)


def validate_tool_config(tool_id: str, tool_config: dict) -> None:
    """
    Validate a tool configuration.

    Args:
        tool_id: The tool identifier (name or toolset.name format).
        tool_config: The tool configuration.

    Raises:
        ValueError: If the tool configuration is invalid.
    """
    if not isinstance(tool_config, dict):
        raise ValueError(f"Tool '{tool_id}' must be a dictionary")

    if 'execution' not in tool_config:
        raise ValueError(f"Tool '{tool_id}' must contain an 'execution' section")

    if not isinstance(tool_config['execution'], dict):
        raise ValueError(f"Execution section in '{tool_id}' must be a dictionary")

    if 'command' not in tool_config['execution']:
        raise ValueError(f"Tool '{tool_id}' execution must contain a 'command'")


def register_parsed_tools(tools_info: list[ToolInfo]) -> None:
    """
    Register tools with MCP based on parsed tool information.

    Args:
        tools_info: List of ToolInfo objects from parse_tools().
    """
    for tool_info in tools_info:
        try:
            # Create a unique namespace for this function
            tool_namespace = {
                "tool_info": tool_info.runtime_info,
                "build_command": build_command,
                "execute_command": execute_command,
            }
            # Execute the code to create the function
            exec(tool_info.exec_code, tool_namespace)
            # Get the created function
            handler = tool_namespace[tool_info.function_name]
            # Register the function with MCP
            mcp.tool(
                name=tool_info.tool_name,
                description=tool_info.get_full_description(),
            )(handler)
        except Exception:
            import traceback
            traceback.print_exc()


def register_prompts(prompts_info: list[PromptInfo]) -> None:
    """
    Register prompts with MCP based on parsed prompt information.

    Args:
        prompts_info: List of PromptInfo objects from parse_prompts().
    """
    for prompt_info in prompts_info:
        try:
            # Create prompt handler function dynamically
            def create_prompt_handler(prompt_info: PromptInfo) -> Callable:

                # Build function signature dynamically based on prompt arguments
                required_args = []
                optional_args = []

                for arg_name, arg_info in prompt_info.arguments.items():
                    if arg_info.required:
                        required_args.append(arg_name)
                    else:
                        optional_args.append(f"{arg_name}: str = ''")

                # Create function signature
                sig_parts = required_args + optional_args
                signature = ", ".join(sig_parts)

                # Create the actual handler function
                func_code = (
                    f"async def handler({signature}) -> str:\n"
                    "    return render_template(template, locals())"
                )

                # Create namespace with the template and renderer
                namespace = {
                    "template": prompt_info.template,
                    "render_template": render_template,
                }

                # Execute the function definition
                exec(func_code, namespace)

                # Return the created function
                return namespace["handler"]

            # Create and register the prompt handler
            handler = create_prompt_handler(prompt_info)
            mcp.prompt(name=prompt_info.name, description=prompt_info.description)(handler)
        except Exception:
            import traceback
            traceback.print_exc()


def register_tools(config: dict) -> None:
    """
    Register tools from configuration.

    Args:
        config: The configuration dictionary.
    """
    tools_info = parse_tools(config)
    register_parsed_tools(tools_info)


def register_all(config: dict) -> None:
    """
    Register both tools and prompts from configuration.

    Args:
        config: The configuration dictionary.
    """
    # Register tools if present
    if 'tools' in config:
        register_tools(config)

    # Register prompts if present
    if 'prompts' in config:
        prompts_info = parse_prompts(config)
        register_prompts(prompts_info)


def init_server(config_path: str | None = None, tools: str | None = None) -> None:
    """
    Initialize the server with the given configuration.

    Args:
        config_path: Path to the YAML configuration file.
                    If None and tools is None, use MCP_THIS_CONFIG_PATH
                    environment variable or default config.
        tools: JSON-structured configuration string.
                    Takes precedence over config_path if both are provided.

    Raises:
        ValueError: If the configuration is invalid.
        FileNotFoundError: If the configuration file does not exist.
        JSONDecodeError: If the JSON configuration string is invalid.
    """
    config = load_config(config_path, tools)
    validate_config(config)
    register_all(config)


def run_server() -> None:
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    # This is used when directly executing the mcp_server.py file
    # For normal usage, the __main__.py entry point should be used
    try:
        # Use environment variable for config path by default
        config_path = os.environ.get("MCP_THIS_CONFIG_PATH")
        tools = None  # No direct JSON input when running as script
        init_server(config_path=config_path, tools=tools)
        run_server()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
