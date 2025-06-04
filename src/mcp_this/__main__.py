#!/usr/bin/env python3
"""
Entry point for mcp-this - MCP Server for CLI tools.

This module provides the main entry point for the mcp-this package, which creates
an MCP server that exposes command-line tools to Claude via the Model-Control-Protocol.
The server reads YAML configuration files to define tools that map to shell commands,
making them available to Claude without requiring any code.
"""

import os
import sys
import argparse
import pathlib
from mcp_this.mcp_server import mcp, init_server

def find_default_config() -> str | None:
    """
    Find the default configuration file in standard locations.

    Returns:
        Optional[str]: Path to the default configuration file, or None if not found
    """
    # Check package configs directory first
    package_dir = pathlib.Path(__file__).parent
    locations = [
        package_dir / "configs" / "default.yaml",
        pathlib.Path.home() / ".config" / "mcp-this" / "config.yaml",
        pathlib.Path("/etc/mcp-this/config.yaml"),
    ]
    for location in locations:
        if location.exists():
            return str(location)
    return None

def get_preset_config(preset_name: str) -> str | None:
    """
    Get the path to a built-in preset configuration.

    Args:
        preset_name: Name of the preset (e.g., 'default', 'editing')

    Returns:
        Optional[str]: Path to the preset configuration file, or None if not found
    """
    package_dir = pathlib.Path(__file__).parent
    preset_path = package_dir / "configs" / f"{preset_name}.yaml"
    if preset_path.exists():
        return str(preset_path)
    return None

def main() -> None:
    """Run the MCP server with the specified configuration."""
    parser = argparse.ArgumentParser(description="Dynamic CLI Tools MCP Server")
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        "--config-path",
        "--config_path",
        type=str,
        help="Path to YAML configuration file",
    )
    config_group.add_argument(
        "--config-value",
        "--config_value",
        type=str,
        help="JSON-structured configuration string",
    )
    config_group.add_argument(
        "--preset",
        type=str,
        help="Built-in preset configuration (e.g., 'default', 'editing')",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )
    args = parser.parse_args()

    # Set config path or value from argument or look for default config
    config_path = None
    tools = None

    # First check explicit arguments
    if args.config_path:
        config_path = args.config_path
    elif args.config_value:
        tools = args.config_value
    elif args.preset:
        config_path = get_preset_config(args.preset)
        if not config_path:
            print(f"Error: Preset '{args.preset}' not found.")
            sys.exit(1)
    # Then check environment variable
    elif os.environ.get("MCP_THIS_CONFIG_PATH"):
        config_path = os.environ.get("MCP_THIS_CONFIG_PATH")
    # Finally look for default configs
    else:
        config_path = find_default_config()

    if not config_path and not tools:
        print("Error: No configuration found. Please provide one using:")
        print("  1. --config-path argument (YAML file)")
        print("  2. --config-value argument (JSON string)")
        print("  3. --preset argument (e.g., 'editing')")
        print("  4. MCP_THIS_CONFIG_PATH environment variable")
        print("  5. Place default.yaml in the package configs directory")
        sys.exit(1)

    try:
        # Initialize the server with the configuration
        init_server(config_path=config_path, tools=tools)
        # Run the MCP server with the specified transport
        mcp.run(transport=args.transport)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
