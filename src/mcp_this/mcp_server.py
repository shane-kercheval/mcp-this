#!/usr/bin/env python3
"""
Dynamic CLI Tool MCP Server

This server creates MCP tools dynamically from a YAML configuration file.
Each tool maps to a command-line command that can be executed by the server.
"""

import os
import yaml
import asyncio
import subprocess
import re
from typing import Optional, Dict, Any

from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Dynamic CLI Tools")

# Get configuration path from environment variable
config_path = os.environ.get("MCP_CONFIG_PATH")
if not config_path:
    print("Error: MCP_CONFIG_PATH environment variable is not set.")
    print("Please set it to the path of your YAML configuration file.")
    exit(1)

if not os.path.isfile(config_path):
    print(f"Error: Configuration file not found: {config_path}")
    exit(1)

print(f"Loading configuration from: {config_path}")

# Load configuration
try:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f"Error loading configuration: {e}")
    exit(1)

# Utility function to build command from template and parameters
def build_command(command_template: str, parameters: Dict[str, Any]) -> str:
    """Build a command from a template and parameters"""
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
    result = " ".join(result.split())
    
    return result

# Execute a command with a working directory
async def execute_command(cmd: str, working_dir: Optional[str] = None) -> str:
    """Execute a shell command"""
    try:
        print(f"Executing command: {cmd}")
        if working_dir:
            print(f"Working directory: {working_dir}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_message = stderr.decode() if stderr else "Unknown error"
            return f"Error executing command: {error_message}"
        
        return stdout.decode()
    except Exception as e:
        return f"Error: {str(e)}"

# Register tools from configuration at module level
if 'toolsets' in config:
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
                    "uses_working_dir": uses_working_dir
                }
                
                # Create parameter string for function definition
                param_parts = []
                for param_name, param_config in parameters.items():
                    if param_config.get('required', False):
                        param_parts.append(f"{param_name}")
                    else:
                        param_parts.append(f"{param_name}: Optional[str] = None")
                
                # Add working_dir parameter if needed
                if uses_working_dir and 'working_dir' not in parameters:
                    param_parts.append("working_dir: Optional[str] = None")
                
                param_string = ", ".join(param_parts)
                
                # Print debug info
                print(f"Creating tool: {full_tool_name}")
                print(f"Function name: {function_name}")
                print(f"Parameters: {param_string}")
                print(f"Command template: {command_template}")
                
                # Create a unique function for each tool
                # We'll use a simple technique to create a function with specific parameters
                # First create a unique namespace for this function
                tool_namespace = {
                    "tool_info": tool_info,
                    "build_command": build_command,
                    "execute_command": execute_command,
                    "Optional": Optional
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
                for param_name in parameters.keys():
                    exec_code += f"    if {param_name} is not None:\n"
                    exec_code += f"        params['{param_name}'] = {param_name}\n"
                
                # Add code to build and execute the command
                exec_code += f"""
    # Get command template from tool_info
    command_template = tool_info["command_template"]
    
    # Build the command
    cmd = build_command(command_template, params)
    
    # Execute the command
"""
                
                if uses_working_dir:
                    exec_code += "    return await execute_command(cmd, working_dir)\n"
                else:
                    exec_code += "    return await execute_command(cmd)\n"
                
                # Execute the code to create the function
                exec(exec_code, tool_namespace)
                
                # Get the created function
                handler = tool_namespace[function_name]
                
                # Register the function with MCP
                mcp.tool(name=full_tool_name, description=full_description)(handler)
                
                print(f"Successfully registered tool: {full_tool_name}")
                
            except Exception as e:
                print(f"Error registering tool '{toolset_name}.{tool_name}': {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run(transport="stdio")