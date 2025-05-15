"""Unit tests for the MCP server."""
import pytest
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SAMPLE_CONFIG_PATH = Path(__file__).parent / "fixtures" / "test_config.yaml"


@pytest.fixture
def server_params():
    """Create server parameters for connecting to our MCP server."""
    assert SAMPLE_CONFIG_PATH.exists(), f"Test config not found at {SAMPLE_CONFIG_PATH}"
    # Return the server parameters with config path as an argument
    return StdioServerParameters(
        command="python",
        args=["-m", "mcp_this", "--config", str(SAMPLE_CONFIG_PATH)],
    )


@pytest.mark.asyncio
async def test_list_tools(server_params: StdioServerParameters):
    """Test that tools are properly registered and can be listed."""
    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()

            # Verify tools exist
            assert tools.tools  # Check that the tools list is not empty

            # Check for specific tools (adjust based on your test config)
            tool_names = [t.name for t in tools.tools]
            assert "example-tool" in tool_names


@pytest.mark.asyncio
async def test_call_tool(server_params: StdioServerParameters):
    """Test that a tool can be called and returns expected results."""
    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Call a tool
            result = await session.call_tool("example-tool", {"name": "World"})
            assert result.content
            # Get the text content from the result (CallToolResult object)
            result_text = result.content[0].text
            # Verify the result
            assert "Hello, World!" in result_text


@pytest.mark.asyncio
async def test_tool_parameters(server_params: StdioServerParameters):
    """Test that tool parameters are correctly defined."""
    async with stdio_client(server_params) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()

            # Find our test tool
            example_tool = next((t for t in tools.tools if t.name == "example-tool"), None)
            assert example_tool is not None

            # Parameters are in the inputSchema property
            assert example_tool.inputSchema is not None
            assert 'properties' in example_tool.inputSchema

            # Check that the 'name' parameter exists
            assert 'name' in example_tool.inputSchema['properties']

            # Parameter is optional (no 'required' list or it's not in that list)
            # In JSON Schema, required fields are listed in a 'required' array at the schema root
            if 'required' in example_tool.inputSchema:
                assert 'name' not in example_tool.inputSchema['required']
