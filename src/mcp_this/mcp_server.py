#!/usr/bin/env python3
"""
MCP Server that dynamically creates command-line tools based on a YAML configuration file.

Each tool maps to a command-line command that can be executed by the server.
"""

import os
import yaml
import asyncio
import subprocess
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import sys


mcp = FastMCP("Dynamic CLI Tools")

# Utility function to build command from template and parameters
def build_command(command_template: str, parameters: dict[str, str]) -> str:
    """Build a command from a template and parameters."""
    result = command_template

    # Replace each parameter placeholder with its value
    for param_name, param_value in parameters.items():
        placeholder = f"<<{param_name}>>"
        if param_value is not None and param_value != "":
            result = result.replace(placeholder, str(param_value))
        else:
            # Remove placeholder if no value provided
            result = result.replace(placeholder, "")

    # Clean up any leftover placeholders (optional parameters not provided)
    result = result.replace("<<", "").replace(">>", "")
    # Clean up multiple spaces
    return " ".join(result.split())


# Execute a command with a working directory
async def execute_command(cmd: str, working_dir: str = '') -> str:  # noqa: PLR0911
    """Execute a shell command."""
    try:
        print(f"Executing command: {cmd}")
        if working_dir:
            print(f"Working directory: {working_dir}")

        # Check if the working directory exists and is accessible
        if working_dir:
            import os
            if not os.path.exists(working_dir):
                return f"Error: Working directory does not exist: {working_dir}"
            if not os.path.isdir(working_dir):
                return f"Error: Working directory is not a directory: {working_dir}"
            if not os.access(working_dir, os.R_OK):
                return f"Error: Working directory is not readable: {working_dir}"

        # If working_dir is empty or None, use None for cwd to use current directory
        effective_cwd = working_dir if working_dir else None

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=effective_cwd,
        )

        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""

        if process.returncode != 0:
            error_message = stderr_text if stderr_text else "Unknown error"
            return f"Error executing command: {error_message}"

        # If stdout is empty, check stderr for any warning messages
        if not stdout_text and stderr_text:
            return f"Command produced no output, but stderr: {stderr_text}"

        return stdout_text
    except Exception as e:
        return f"Error: {e!s}"


def get_default_config_path() -> Path | None:
    """Get the path to the default configuration file."""
    # Look for default config in package directory
    package_dir = Path(__file__).parent
    default_config = package_dir / "config" / "default.yaml"
    if default_config.exists():
        return default_config
    return None


def load_config(config_path: str | None = None) -> dict:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.
                    If None, use MCP_THIS_CONFIG_PATH environment variable or default config.

    Returns:
        The loaded configuration dictionary.

    Raises:
        ValueError: If no configuration path is provided and MCP_THIS_CONFIG_PATH is not set.
        FileNotFoundError: If the configuration file does not exist.
    """
    if not config_path:
        config_path = os.environ.get("MCP_THIS_CONFIG_PATH")

    if not config_path:
        # Try to use default config
        default_path = get_default_config_path()
        if default_path:
            config_path = str(default_path)
        else:
            raise ValueError(
                "No configuration path provided. Please set MCP_THIS_CONFIG_PATH environment variable, "  # noqa: E501
                "pass a path, or include a default configuration in the package.",
            )

    config_path_obj = Path(config_path)
    if not config_path_obj.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    print(f"Loading configuration from: {config_path}")
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

    if 'toolsets' not in config:
        raise ValueError("Configuration must contain a 'toolsets' section")

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
            if not isinstance(tool_config, dict):
                raise ValueError(f"Tool '{toolset_name}.{tool_name}' must be a dictionary")

            if 'execution' not in tool_config:
                raise ValueError(f"Tool '{toolset_name}.{tool_name}' must contain an 'execution' section")  # noqa: E501

            if not isinstance(tool_config['execution'], dict):
                raise ValueError(f"Execution section in '{toolset_name}.{tool_name}' must be a dictionary")  # noqa: E501

            if 'command' not in tool_config['execution']:
                raise ValueError(f"Tool '{toolset_name}.{tool_name}' execution must contain a 'command'")  # noqa: E501


def register_tools(config: dict) -> None:  # noqa: PLR0912
    """
    Register tools from configuration.

    Args:
        config: The configuration dictionary.
    """
    if 'toolsets' not in config:
        print("No toolsets found in configuration")
        return

    toolsets = config['toolsets']
    print(f"Found {len(toolsets)} toolset(s) in configuration")

    for toolset_name, toolset_config in toolsets.items():
        tools = toolset_config.get('tools', {})
        print(f"Processing toolset '{toolset_name}' with {len(tools)} tools")

        for tool_name, tool_config in tools.items():
            try:
                # Determine the full tool name
                if tool_name == toolset_name:
                    full_tool_name = tool_name
                else:
                    full_tool_name = f"{toolset_name}-{tool_name}"

                # Create a valid Python identifier for the function name
                function_name = re.sub(r'[^a-zA-Z0-9_]', '_', full_tool_name)

                # Get execution configuration
                execution = tool_config.get('execution', {})
                command_template = execution.get('command', '')
                uses_working_dir = execution.get('uses_working_dir', False)

                # Get description and help text
                description = tool_config.get('description', '')
                help_text = tool_config.get('help_text', '')
                full_description = f"{description}\n\n{help_text}" if help_text else description

                # Get parameters configuration
                parameters = tool_config.get('parameters', {})

                # Save a copy of the command template and parameter names for this specific tool
                tool_info = {
                    "command_template": command_template,
                    "parameters": list(parameters.keys()),
                    "uses_working_dir": uses_working_dir,
                }

                # Create parameter string for function definition
                param_parts = []
                for param_name, param_config in parameters.items():
                    if param_config.get('required', False):
                        param_parts.append(f"{param_name}")
                    else:
                        # Use str with empty string default for optional parameters
                        # instead of Optional[str] to avoid MCP inspector issues
                        param_parts.append(f"{param_name}: str = ''")

                # Add working_dir parameter if needed
                if uses_working_dir and 'working_dir' not in parameters:
                    # Using str with empty string default, not Optional[str]
                    param_parts.append("working_dir: str = ''")

                param_string = ", ".join(param_parts)
                # Create a unique function for each tool
                # We'll use a simple technique to create a function with specific parameters
                # First create a unique namespace for this function
                tool_namespace = {
                    "tool_info": tool_info,
                    "build_command": build_command,
                    "execute_command": execute_command,
                }

                # Create the function definition code
                exec_code = f"""
async def {function_name}({param_string}) -> str:
    \"\"\"
    {full_description}
    \"\"\"
    # Collect parameters
    params = {{}}
"""

                # Add code to collect parameters
                for param_name in parameters:
                    # Include parameters even if they're empty strings
                    # This handles the case of str = '' default values
                    exec_code += f"    params['{param_name}'] = {param_name}\n"

                # Add code to build and execute the command
                exec_code += """
    # Get command template from tool_info
    command_template = tool_info["command_template"]

    # Build the command
    cmd = build_command(command_template, params)

    # Execute the command
"""

                # Check if the working_dir is a parameter specified in the tool config
                if uses_working_dir:
                    if 'working_dir' in parameters:
                        # If working_dir is in parameters, use that value from params
                        exec_code += "    return await execute_command(cmd, params.get('working_dir', ''))\n"  # noqa: E501
                    else:
                        # Otherwise use the working_dir from function parameter
                        exec_code += "    return await execute_command(cmd, working_dir)\n"
                else:
                    exec_code += "    return await execute_command(cmd)\n"

                # Execute the code to create the function
                exec(exec_code, tool_namespace)
                # Get the created function
                handler = tool_namespace[function_name]
                # Register the function with MCP
                mcp.tool(name=full_tool_name, description=full_description)(handler)
            except Exception:
                import traceback
                traceback.print_exc()


def init_server(config_path: str | None = None) -> None:
    """
    Initialize the server with the given configuration.

    Args:
        config_path: Path to the YAML configuration file.
                    If None, use MCP_THIS_CONFIG_PATH environment variable or default config.

    Raises:
        ValueError: If the configuration is invalid.
        FileNotFoundError: If the configuration file does not exist.
    """
    config = load_config(config_path)
    validate_config(config)
    register_tools(config)


def run_server() -> None:
    """Run the MCP server."""
    print("Starting MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":

    try:
        # Use environment variable for config path by default
        config_path = os.environ.get("MCP_THIS_CONFIG_PATH")
        init_server(config_path)
        run_server()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


