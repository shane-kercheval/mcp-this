#!/usr/bin/env python3
"""
Test server to diagnose parameter handling issues in FastMCP
"""

import asyncio
import subprocess
from typing import Optional, Dict, Any

from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Test MCP Server")

async def execute_command(cmd: str, cwd: Optional[str] = None) -> str:
    """Execute a shell command"""
    try:
        print(f"Executing command: {cmd}")
        if cwd:
            print(f"Working directory: {cwd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_message = stderr.decode() if stderr else "Unknown error"
            return f"Error executing command: {error_message}"
        
        return stdout.decode()
    except Exception as e:
        return f"Error: {str(e)}"

# Test 1: Required string parameter
@mcp.tool(name="test-required", description="Test with a required parameter")
async def test_required(pattern: str) -> str:
    """Test with a required parameter."""
    return f"Got pattern: {pattern}"

# Test 2: Optional string parameter with default None
@mcp.tool(name="test-optional-none", description="Test with an optional parameter (default None)")
async def test_optional_none(pattern: Optional[str] = None) -> str:
    """Test with an optional parameter (default None)."""
    return f"Got pattern: {pattern}"

# Test 3: Optional string parameter with default empty string
@mcp.tool(name="test-optional-empty", description="Test with an optional parameter (default empty)")
async def test_optional_empty(pattern: str = "") -> str:
    """Test with an optional parameter (default empty)."""
    return f"Got pattern: '{pattern}'"

# Test 4: Optional string parameter with default value
@mcp.tool(name="test-optional-default", description="Test with an optional parameter (with default)")
async def test_optional_default(pattern: str = "*.txt") -> str:
    """Test with an optional parameter (with default)."""
    return f"Got pattern: {pattern}"

# Test 5: Working directory parameter
@mcp.tool(name="test-working-dir", description="Test with a working directory parameter")
async def test_working_dir(pattern: str, working_dir: str = '') -> str:
    """Test with a working directory parameter."""
    cmd = f'find . -name "{pattern}" -type f'
    return await execute_command(cmd, working_dir)

# Test 6: Optional working directory parameter
@mcp.tool(name="test-optional-working-dir", description="Test with an optional working directory parameter")
async def test_optional_working_dir(pattern: str, working_dir: Optional[str] = None) -> str:
    """Test with an optional working directory parameter."""
    cmd = f'find . -name "{pattern}" -type f'
    return await execute_command(cmd, working_dir)

# Test 7: Renamed working directory parameter
@mcp.tool(name="test-renamed-dir", description="Test with a renamed working directory parameter")
async def test_renamed_dir(pattern: str, work_dir: Optional[str] = None) -> str:
    """Test with a renamed working directory parameter."""
    cmd = f'find . -name "{pattern}" -type f'
    return await execute_command(cmd, work_dir)

# Test 8: Integer parameter
@mcp.tool(name="test-integer", description="Test with an integer parameter")
async def test_integer(pattern: str, count: int = 5) -> str:
    """Test with an integer parameter."""
    return f"Got pattern: {pattern}, count: {count}"

if __name__ == "__main__":
    print("Starting Test MCP server...")
    mcp.run(transport="stdio")