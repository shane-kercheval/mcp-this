"""Unit tests for the MCP server."""
import pytest
import json
import yaml
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SAMPLE_CONFIG_PATH = Path(__file__).parent / "fixtures" / "test_config.yaml"


@pytest.fixture
def server_params_config_path():
    """Create server parameters using --config_path argument."""
    assert SAMPLE_CONFIG_PATH.exists(), f"Test config not found at {SAMPLE_CONFIG_PATH}"
    # Return the server parameters with config path as an argument
    return StdioServerParameters(
        command="python",
        args=["-m", "mcp_this", "--config_path", str(SAMPLE_CONFIG_PATH)],
    )


@pytest.fixture
def server_params_config_value():
    """Create server parameters using --config_value argument with JSON."""
    import json
    import yaml
    
    # Read the test config file and convert it to JSON
    assert SAMPLE_CONFIG_PATH.exists(), f"Test config not found at {SAMPLE_CONFIG_PATH}"
    with open(SAMPLE_CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    
    # Convert the config to JSON string
    config_json = json.dumps(config)
    
    # Return the server parameters with config value as an argument
    return StdioServerParameters(
        command="python",
        args=["-m", "mcp_this", "--config_value", config_json],
    )


# Test with --config_path
@pytest.mark.asyncio
async def test_list_tools_config_path(server_params_config_path):
    """Test that tools are properly registered and can be listed using config_path."""
    async with stdio_client(server_params_config_path) as (read, write):  # noqa: SIM117
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
async def test_call_tool_config_path(server_params_config_path):
    """Test that a tool can be called and returns expected results using config_path."""
    async with stdio_client(server_params_config_path) as (read, write):  # noqa: SIM117
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
async def test_tool_parameters_config_path(server_params_config_path):
    """Test that tool parameters are correctly defined using config_path."""
    async with stdio_client(server_params_config_path) as (read, write):  # noqa: SIM117
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


# Test with --config_value
@pytest.mark.asyncio
async def test_list_tools_config_value(server_params_config_value):
    """Test that tools are properly registered and can be listed using config_value."""
    async with stdio_client(server_params_config_value) as (read, write):  # noqa: SIM117
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
async def test_call_tool_config_value(server_params_config_value):
    """Test that a tool can be called and returns expected results using config_value."""
    async with stdio_client(server_params_config_value) as (read, write):  # noqa: SIM117
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
async def test_tool_parameters_config_value(server_params_config_value):
    """Test that tool parameters are correctly defined using config_value."""
    async with stdio_client(server_params_config_value) as (read, write):  # noqa: SIM117
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
