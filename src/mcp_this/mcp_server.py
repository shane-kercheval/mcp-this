#!/usr/bin/env python3
"""
MCP Server that dynamically creates command-line tools based on a YAML configuration file.

Each tool maps to a command-line command that can be executed by the server.
"""
import os
from textwrap import dedent
import yaml
import json
import re
import asyncio
import subprocess
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from dataclasses import dataclass
import sys

@dataclass
class ToolInfo:
    """Information about a parsed tool from the configuration."""

    toolset_name: str
    tool_name: str
    full_tool_name: str
    function_name: str
    command_template: str
    uses_working_dir: bool
    description: str
    parameters: dict[str, dict]
    param_string: str
    exec_code: str
    runtime_info: dict[str, any]  # Information needed by the generated function at runtime

    def get_full_description(self) -> str:
        """
        Build a comprehensive Python-style docstring for the tool.

        Includes the tool description followed by the command template,
        then parameter descriptions in standard docstring format.

        Returns:
            A formatted docstring with the tool description, command template, and parameter
            details.
        """
        # Start with the tool description
        lines = [self.description.strip()]

        # Add a blank line and the command template
        lines.append("")
        lines.append("Command: " + self.command_template)

        # Add Args section if there are parameters
        if self.parameters:
            lines.append("")
            lines.append("Args:")

            # Add each parameter with its description
            for param_name, param_config in self.parameters.items():
                desc = param_config.get("description", "")
                required = param_config.get("required", False)
                req_text = " (required)" if required else " (optional)"
                lines.append(f"    {param_name}: {desc}{req_text}")

        # Add working_dir parameter if not explicitly included but used
        if self.uses_working_dir and "working_dir" not in self.parameters:
            lines.append("    working_dir: Directory to run the command in (optional)")

        # Join all lines with newlines to form the complete docstring
        return "\n".join(lines)


mcp = FastMCP("Dynamic CLI Tools")


def build_command(command_template: str, parameters: dict[str, str]) -> str:
    r"""
    Build a shell command from a template by substituting parameter placeholders.

    Parameters are specified in the template using the format `<<parameter_name>>`.
    When a parameter value is provided, its placeholder is replaced with the value.
    If a parameter value is empty or None, the placeholder is removed completely.
    Any parameter not found in the parameters dictionary will have its placeholder removed.
    Any leftover placeholders are removed, and multiple spaces are normalized.

    Args:
        command_template: The command template with parameter placeholders.
            Example: "tail -n <<lines>> -f \"<<file>>\""
        parameters: Dictionary mapping parameter names to their values.
            Example: {"lines": 10, "file": "/var/log/syslog"}

    Returns:
        The processed command string with parameters substituted and cleaned up.
        Example: "tail -n 10 -f \"/var/log/syslog\""
    """
    result = command_template

    # Replace each parameter placeholder with its value
    for param_name, param_value in parameters.items():
        placeholder = f"<<{param_name}>>"
        if param_value is not None and param_value != "":
            result = result.replace(placeholder, str(param_value))
        else:
            # Remove placeholder if no value provided
            result = result.replace(placeholder, "")

    # Find any remaining placeholders (parameters not in the dictionary)
    remaining_placeholders = re.findall(r'<<\w+>>', result)
    # Remove each remaining placeholder
    for placeholder in remaining_placeholders:
        result = result.replace(placeholder, "")
    # Clean up multiple spaces
    return " ".join(result.split())


async def execute_command(cmd: str, working_dir: str | None = None) -> str:  # noqa: PLR0911
    """
    Execute a shell command asynchronously and return its output.

    This function runs a shell command in a subprocess and captures both stdout and stderr.
    It handles various error conditions such as invalid working directories, command execution
    failures, and unexpected exceptions. The command output or error message is returned as a
    string.

    Args:
        cmd: The shell command to execute.
            Example: "ls -la /tmp"
        working_dir: Optional directory to use as the working directory for the command.
            If empty or None, the current working directory is used.

    Returns:
        A string containing one of the following:
        - The stdout output if the command succeeds and produces output
        - The stderr output if the command succeeds but stdout is empty
        - An error message if the command fails or an exception occurs

    Notes:
        - The function validates the working directory's existence and permissions before execution
        - Both stdout and stderr are captured and decoded as text
        - Non-zero return codes result in an error message being returned
        - Any exceptions during execution are caught and returned as error messages
    """
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


def load_config(config_path: str | None = None, config_value: str | None = None) -> dict:
    """
    Load configuration from a YAML file or JSON string.

    Args:
        config_path: Path to the YAML configuration file.
                    If None and config_value is None, use MCP_THIS_CONFIG_PATH environment variable
                    or default config.
        config_value: JSON-structured configuration string.
                    Takes precedence over config_path if both are provided.

    Returns:
        The loaded configuration dictionary.

    Raises:
        ValueError: If no configuration source is provided.
        FileNotFoundError: If the configuration file does not exist.
        JSONDecodeError: If the JSON configuration string is invalid.
    """
    # Priority: config_value > config_path > env var > default config
    if config_value:
        print("Loading configuration from JSON string")
        try:
            config = json.loads(config_value)
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


def parse_tools(config: dict) -> list[ToolInfo]:  # noqa: PLR0912
    """
    Parse tools from configuration and extract all necessary information.

    Args:
        config: The configuration dictionary.

    Returns:
        A list of ToolInfo objects, each containing information about a tool.
    """
    if 'toolsets' not in config:
        print("No toolsets found in configuration")
        return []

    tools_info = []
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
                execution = tool_config['execution']
                command_template = execution['command']
                uses_working_dir = execution.get('uses_working_dir', False)

                # Get description
                description = tool_config.get('description', '')
                # Get parameters configuration
                parameters = tool_config.get('parameters', {})

                # Save a copy of the command template and parameter names for this specific tool
                runtime_info = {
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

                # Create the function definition code
                exec_code = dedent(f"""
                async def {function_name}({param_string}) -> str:
                    \"\"\"
                    {description}
                    \"\"\"
                    # Collect parameters
                    params = {{}}
                """)

                # Add code to collect parameters
                for param_name in parameters:
                    # Include parameters even if they're empty strings
                    # This handles the case of str = '' default values
                    exec_code += f"    params['{param_name}'] = {param_name}\n"

                # Add code to build and execute the command
                temp_code = dedent("""
                    # Get command template from tool_info
                    command_template = tool_info["command_template"]
                    # Build the command
                    cmd = build_command(command_template, params)
                    # Execute the command
                """)
                # re-indent 4 spaces
                exec_code += "\n".join("    " + line for line in temp_code.splitlines()) + "    \n"

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

                # Create a ToolInfo object instead of a dictionary
                tool_info = ToolInfo(
                    toolset_name=toolset_name,
                    tool_name=tool_name,
                    full_tool_name=full_tool_name,
                    function_name=function_name,
                    command_template=command_template,
                    uses_working_dir=uses_working_dir,
                    description=description,
                    parameters=parameters,
                    param_string=param_string,
                    exec_code=exec_code,
                    runtime_info=runtime_info,
                )
                tools_info.append(tool_info)
            except Exception:
                import traceback
                traceback.print_exc()

    return tools_info


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


def init_server(config_path: str | None = None, config_value: str | None = None) -> None:
    """
    Initialize the server with the given configuration.

    Args:
        config_path: Path to the YAML configuration file.
                    If None and config_value is None, use MCP_THIS_CONFIG_PATH
                    environment variable or default config.
        config_value: JSON-structured configuration string.
                    Takes precedence over config_path if both are provided.

    Raises:
        ValueError: If the configuration is invalid.
        FileNotFoundError: If the configuration file does not exist.
        JSONDecodeError: If the JSON configuration string is invalid.
    """
    config = load_config(config_path, config_value)
    validate_config(config)
    register_tools(config)


def run_server() -> None:
    """Run the MCP server."""
    print("Starting MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    # This is used when directly executing the mcp_server.py file
    # For normal usage, the __main__.py entry point should be used
    try:
        # Use environment variable for config path by default
        config_path = os.environ.get("MCP_THIS_CONFIG_PATH")
        config_value = None  # No direct JSON input when running as script
        init_server(config_path=config_path, config_value=config_value)
        run_server()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
