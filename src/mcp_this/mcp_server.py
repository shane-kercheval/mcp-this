#!/usr/bin/env python3
"""
MCP Server that dynamically creates command-line tools based on a YAML configuration file.

Each tool maps to a command-line command that can be executed by the server.
"""
import os
import yaml
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import sys
from mcp_this.tools import ToolInfo, build_command, execute_command, parse_tools


mcp = FastMCP("Dynamic CLI Tools")


def get_default_tools_path() -> Path | None:
    """Get the path to the default configuration file."""
    # Look for default config in package directory
    package_dir = Path(__file__).parent
    # Correct path where the file is stored
    default_config = package_dir / "configs" / "default.yaml"
    if default_config.exists():
        return default_config
    return None


def load_config(tools_path: str | None = None, tools: str | None = None) -> dict:
    """
    Load configuration from a YAML file or JSON string.

    Args:
        tools_path: Path to the YAML configuration file.
                    If None and tools is None, use MCP_THIS_CONFIG_PATH environment variable
                    or default config.
        tools: JSON-structured configuration string.
                    Takes precedence over tools_path if both are provided.

    Returns:
        The loaded configuration dictionary.

    Raises:
        ValueError: If no configuration source is provided.
        FileNotFoundError: If the configuration file does not exist.
        JSONDecodeError: If the JSON configuration string is invalid.
    """
    # Priority: tools > tools_path > env var > default config
    if tools:
        try:
            config = json.loads(tools)
            if not config:
                raise ValueError("Configuration value is empty")
            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON configuration: {e}")

    if not tools_path:
        tools_path = os.environ.get("MCP_THIS_CONFIG_PATH")

    if not tools_path:
        # Try to use default config
        default_path = get_default_tools_path()
        if default_path:
            tools_path = str(default_path)
        else:
            raise ValueError(
                "No configuration provided. Please provide --tools_path, --tools, "
                "set MCP_THIS_CONFIG_PATH environment variable, "
                "or include a default configuration in the package.",
            )

    tools_path_obj = Path(tools_path)
    if not tools_path_obj.is_file():
        raise FileNotFoundError(f"Configuration file not found: {tools_path}")

    # Load configuration
    try:
        with open(tools_path_obj) as f:
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

    # Check if we have either a top-level tools section or a toolsets section
    if 'tools' not in config and 'toolsets' not in config:
        raise ValueError("Configuration must contain either a 'tools' or 'toolsets' section")

    # Validate top-level tools section if present
    if 'tools' in config:
        if not isinstance(config['tools'], dict):
            raise ValueError("'tools' must be a dictionary")

        for tool_name, tool_config in config['tools'].items():
            validate_tool_config(tool_name, tool_config)

    # Validate toolsets section if present
    if 'toolsets' in config:
        if not isinstance(config['toolsets'], dict):
            raise ValueError("'toolsets' must be a dictionary")

        for toolset_name, toolset_config in config['toolsets'].items():
            if not isinstance(toolset_config, dict):
                raise ValueError(f"Toolset '{toolset_name}' must be a dictionary")

            if 'tools' not in toolset_config:
                raise ValueError(f"Toolset '{toolset_name}' must contain a 'tools' section")

            if not isinstance(toolset_config['tools'], dict):
                raise ValueError(f"Tools in toolset '{toolset_name}' must be a dictionary")

            for tool_name, tool_config in toolset_config['tools'].items():
                validate_tool_config(f"{toolset_name}.{tool_name}", tool_config)


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
                name=tool_info.full_tool_name,
                description=tool_info.get_full_description(),
            )(handler)
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


def init_server(tools_path: str | None = None, tools: str | None = None) -> None:
    """
    Initialize the server with the given configuration.

    Args:
        tools_path: Path to the YAML configuration file.
                    If None and tools is None, use MCP_THIS_CONFIG_PATH
                    environment variable or default config.
        tools: JSON-structured configuration string.
                    Takes precedence over tools_path if both are provided.

    Raises:
        ValueError: If the configuration is invalid.
        FileNotFoundError: If the configuration file does not exist.
        JSONDecodeError: If the JSON configuration string is invalid.
    """
    config = load_config(tools_path, tools)
    validate_config(config)
    register_tools(config)


def run_server() -> None:
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    # This is used when directly executing the mcp_server.py file
    # For normal usage, the __main__.py entry point should be used
    try:
        # Use environment variable for config path by default
        tools_path = os.environ.get("MCP_THIS_CONFIG_PATH")
        tools = None  # No direct JSON input when running as script
        init_server(tools_path=tools_path, tools=tools)
        run_server()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
