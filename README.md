# project-template




To use this server, you would:

Make sure your commands.yaml file is in the same directory
Run python dynamic_cli_server.py to start the server
Or use mcp dev dynamic_cli_server.py to test with the MCP Inspector
Or use mcp install dynamic_cli_server.py to install in Claude Desktop



full path needed?????
{
  "mcpServers": {
    "dynamic-cli-tools": {
      "command": "python",
      "args": [
        "path/to/dynamic_cli_server.py"
      ],
      "env": {
        "MCP_CONFIG_PATH": "path/to/commands.yaml"
      }
    }
  }
}




#!/usr/bin/env python3
"""
Installation helper for Dynamic CLI Tools MCP Server

This script generates the configuration file for Claude Desktop
and provides instructions on how to install the server.
"""

import os
import json
import argparse
import shutil
from pathlib import Path

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Installation helper for Dynamic CLI Tool MCP Server")
    parser.add_argument("--config", "-c", default="commands.yaml",
                        help="Path to the YAML configuration file (default: commands.yaml)")
    parser.add_argument("--name", "-n", default="dynamic-cli-tools",
                        help="Name for the MCP server in Claude Desktop (default: dynamic-cli-tools)")
    return parser.parse_args()

def generate_claude_config(server_name, config_path):
    """Generate Claude Desktop configuration file"""
    # Get the absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(script_dir, "dynamic_cli_server.py")
    config_path = os.path.join(script_dir, config_path)
    
    # Create the configuration
    config = {
        "mcpServers": {
            server_name: {
                "command": "python",
                "args": [
                    server_path,
                    "--config",
                    config_path
                ]
            }
        }
    }
    
    # Determine Claude Desktop config path
    if os.name == 'posix':  # macOS/Linux
        config_dir = os.path.expanduser("~/Library/Application Support/Claude")
    else:  # Windows
        config_dir = os.path.join(os.getenv("APPDATA"), "Claude")
    
    # Create the directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # Path to the Claude Desktop config file
    claude_config_path = os.path.join(config_dir, "claude_desktop_config.json")
    
    # Update existing config if it exists
    if os.path.exists(claude_config_path):
        try:
            with open(claude_config_path, 'r') as f:
                existing_config = json.load(f)
            
            # Update the servers section
            if "mcpServers" not in existing_config:
                existing_config["mcpServers"] = {}
            
            existing_config["mcpServers"][server_name] = config["mcpServers"][server_name]
            config = existing_config
            
            print(f"Updating existing Claude Desktop configuration at: {claude_config_path}")
        except Exception as e:
            print(f"Error reading existing config, will create a new one: {e}")
    else:
        print(f"Creating new Claude Desktop configuration at: {claude_config_path}")
    
    # Write the configuration
    with open(claude_config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return claude_config_path

def main():
    """Main function"""
    args = parse_args()
    
    print("Installing Dynamic CLI Tool MCP Server for Claude Desktop...")
    
    # Generate Claude Desktop configuration
    config_path = generate_claude_config(args.name, args.config)
    
    print("\nInstallation complete!")
    print("\nConfiguration has been written to:")
    print(f"  {config_path}")
    print("\nTo use the server in Claude Desktop:")
    print("1. Restart Claude Desktop if it's currently running")
    print(f"2. Look for the '{args.name}' server in Claude Desktop")
    print("\nYou can also test the server using the MCP Inspector:")
    print(f"  mcp dev dynamic_cli_server.py --config {args.config}")
    
if __name__ == "__main__":
    main()






With these files:

dynamic_cli_server.py - The main server that accepts a config parameter
commands.yaml - Your YAML configuration with all the CLI tools
claude_desktop_config.json - Configuration for Claude Desktop (automatically created by the install script)
install.py - Helper script to install the server for Claude Desktop

You can then install the server by running:
bashpython install.py
This will:

Create/update the Claude Desktop configuration
Set up the server to use your commands.yaml file
Provide instructions for using the server with Claude Desktop

This approach makes it easy to distribute your server to others who can simply run the install script to set it up with their Claude Desktop installation.




- `make tests`
- `make app`


## Misc

- Add a new dependency: `uv add <package>`
- Add a new `dev` dependency: `uv add <package> --group dev`
