"""Helper functions and classes for managing tools and commands."""
import re
import traceback
import asyncio
import subprocess
from dataclasses import dataclass


@dataclass
class ToolInfo:
    """Information about a parsed tool from the configuration."""

    tool_name: str
    full_tool_name: str
    function_name: str
    command_template: str
    description: str
    parameters: dict[str, dict]
    param_string: str
    exec_code: str
    runtime_info: dict[str, any]  # Information needed by the generated function at runtime
    toolset_name: str = None  # Optional, could be None for top-level tools

    def get_full_description(self) -> str:
        """
        Build a comprehensive description optimized for LLM function calling.

        Format is designed to help LLMs understand the tool purpose,
        command structure, and parameter requirements clearly.

        Returns:
            A formatted description with key sections highlighted for LLM processing.
        """
        lines = []

        # Start with a clear TOOL DESCRIPTION section
        lines.append("TOOL DESCRIPTION:")
        lines.append("")
        lines.append(self.description.strip())

        # Add the COMMAND section showing the template
        lines.append("")
        lines.append("COMMAND CALLED:")
        lines.append("")
        lines.append(f"`{self.command_template}`")

        # Add clarification on what the placeholders mean, if there are parameters
        if "<<" in self.command_template and self.parameters:
            # Get the first parameter name to use as example
            first_param = next(iter(self.parameters.keys()), "parameter")
            lines.append("")
            lines.append(f"Text like <<parameter_name>> (e.g. <<{first_param}>>) will be replaced with parameter values.")  # noqa: E501

        # Add PARAMETERS section with clearly marked requirements
        if self.parameters:
            lines.append("")
            lines.append("PARAMETERS:")
            lines.append("")

            # Add each parameter with its description and inferred type
            for param_name, param_config in self.parameters.items():
                desc = param_config.get("description", "")
                required = param_config.get("required", False)
                req_status = "[REQUIRED]" if required else "[OPTIONAL]"

                # All parameters are treated as strings for CLI commands
                param_type = "(string)"

                lines.append(f"- {param_name} {req_status}{' ' + param_type if param_type else ''}: {desc}")  # noqa: E501


        # Add NOTES section if the command could have side effects
        cmd_lower = self.command_template.lower()
        dangerous_operations = ["rm ", "remove ", "delete ", "mv ", "move ", "write ", "create "]
        file_write_operators = [" > ", " >> ", "echo ", "cat ", "touch "]

        has_dangerous_operation = any(op in cmd_lower for op in dangerous_operations)
        has_file_write_operation = any(op in cmd_lower for op in file_write_operators)

        if has_dangerous_operation or has_file_write_operation:
            lines.append("")
            lines.append("IMPORTANT NOTES:")
            lines.append("")
            if any(op in cmd_lower for op in ["rm ", "remove ", "delete "]):
                lines.append("- This command can DELETE files or data. Use with caution.")
            if any(op in cmd_lower for op in ["mv ", "move "]):
                lines.append("- This command can MOVE files or data. Verify paths are correct.")
            if any(op in cmd_lower for op in ["write ", "create "]) or " > " in cmd_lower or " >> " in cmd_lower:  # noqa: E501
                lines.append("- This command can CREATE or MODIFY files or data.")

        # Join all lines with newlines to form the complete description
        return "\n".join(lines)



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


async def execute_command(cmd: str) -> str:
    """
    Execute a shell command asynchronously and return its output.

    This function runs a shell command in a subprocess and captures both stdout and stderr.
    It handles command execution failures and unexpected exceptions. The command output or
    error message is returned as a string.

    Args:
        cmd: The shell command to execute.
            Example: "ls -la /tmp"

    Returns:
        A string containing one of the following:
        - The stdout output if the command succeeds and produces output
        - The stderr output if the command succeeds but stdout is empty
        - An error message if the command fails or an exception occurs

    Notes:
        - Both stdout and stderr are captured and decoded as text
        - Non-zero return codes result in an error message being returned
        - Any exceptions during execution are caught and returned as error messages
    """
    try:
        print(f"Executing command: {cmd}")

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=None,
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



def parse_tools(config: dict) -> list[ToolInfo]:
    """
    Parse tools from configuration and extract all necessary information.

    Args:
        config: The configuration dictionary.

    Returns:
        A list of ToolInfo objects, each containing information about a tool.
    """
    tools_info = []

    # Handle top-level tools if present
    if 'tools' in config:
        top_level_tools = config['tools']
        for tool_name, tool_config in top_level_tools.items():
            try:
                tool_info = create_tool_info(None, tool_name, tool_config)
                tools_info.append(tool_info)
            except Exception:
                traceback.print_exc()

    # Handle tools within toolsets if present
    if 'toolsets' in config:
        toolsets = config['toolsets']
        for toolset_name, toolset_config in toolsets.items():
            tools = toolset_config.get('tools', {})
            for tool_name, tool_config in tools.items():
                try:
                    tool_info = create_tool_info(toolset_name, tool_name, tool_config)
                    tools_info.append(tool_info)
                except Exception:
                    traceback.print_exc()

    return tools_info


def create_tool_info(toolset_name: str, tool_name: str, tool_config: dict) -> ToolInfo:
    """
    Create a ToolInfo object from tool configuration.

    Args:
        toolset_name: The name of the toolset (can be None for top-level tools).
        tool_name: The name of the tool.
        tool_config: The tool configuration.

    Returns:
        A ToolInfo object.
    """
    # Determine the full tool name
    if toolset_name is None:
        # For top-level tools, full name is the same as tool name
        full_tool_name = tool_name
    elif tool_name == toolset_name:
        # For tools with same name as toolset, don't prefix
        full_tool_name = tool_name
    else:
        # Standard case: prefix toolset name
        full_tool_name = f"{toolset_name}-{tool_name}"

    # Create a valid Python identifier for the function name
    function_name = re.sub(r'[^a-zA-Z0-9_]', '_', full_tool_name)

    # Get execution configuration
    execution = tool_config['execution']
    command_template = execution['command']

    # Get description
    description = tool_config.get('description', '')
    # Get parameters configuration
    parameters = tool_config.get('parameters', {})

    # Save a copy of the command template and parameter names for this specific tool
    runtime_info = {
        "command_template": command_template,
        "parameters": list(parameters.keys()),
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


    param_string = ", ".join(param_parts)

    # Create a multi-line string for the function definition with explicit indentation
    # We carefully control where the indentation starts to ensure it works with exec()
    code_lines = [
        f"async def {function_name}({param_string}) -> str:",
        '    """',
        f'    {description}',
        '    """',
        '    # Collect parameters',
        '    params = {}',
    ]
    exec_code = "\n".join(code_lines) + "\n"

    # Add code to collect parameters
    for param_name in parameters:
        # Include parameters even if they're empty strings
        # This handles the case of str = '' default values
        exec_code += f"    params['{param_name}'] = {param_name}\n"

    # Add code to build and execute the command with consistent indentation
    command_code_lines = [
        '    # Get command template from tool_info',
        '    command_template = tool_info["command_template"]',
        '    # Build the command',
        '    cmd = build_command(command_template, params)',
        '    # Execute the command',
    ]
    exec_code += "\n".join(command_code_lines) + "\n"

    # Execute the command with no working directory
    exec_code += "    return await execute_command(cmd)\n"

    # Create a ToolInfo object
    return ToolInfo(
        toolset_name=toolset_name,
        tool_name=tool_name,
        full_tool_name=full_tool_name,
        function_name=function_name,
        command_template=command_template,
        description=description,
        parameters=parameters,
        param_string=param_string,
        exec_code=exec_code,
        runtime_info=runtime_info,
    )

