#!/usr/bin/env python3
"""Entry point for mcp-this."""

import os
import sys
import argparse
import pathlib
from mcp_this.mcp_server import mcp

def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Dynamic CLI Tools MCP Server")
    parser.add_argument("--config", type=str, help="Path to YAML configuration file")
    args = parser.parse_args()
    
    # Set config path from argument or look for default config
    if args.config:
        os.environ["MCP_CONFIG_PATH"] = args.config
    elif not os.environ.get("MCP_CONFIG_PATH"):
        # Look for default config in package directory
        package_dir = pathlib.Path(__file__).parent
        default_config = package_dir / "config" / "default.yaml"
        if default_config.exists():
            os.environ["MCP_CONFIG_PATH"] = str(default_config)
        else:
            print("Error: No configuration file specified. Use --config or set MCP_CONFIG_PATH.")
            sys.exit(1)
    
    # Run the MCP server
    print(f"Starting MCP server with config: {os.environ.get('MCP_CONFIG_PATH')}")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
    