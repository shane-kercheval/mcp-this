"""Unit tests for the MCP server."""
import pytest
import json
import yaml
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SAMPLE_CONFIG_PATH = Path(__file__).parent / "fixtures" / "test_config.yaml"


def get_config_json():
    """Read the test config file and convert it to JSON."""
    assert SAMPLE_CONFIG_PATH.exists(), f"Test config not found at {SAMPLE_CONFIG_PATH}"
    with open(SAMPLE_CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    return json.dumps(config)


@pytest.fixture(
    params=[
        pytest.param(("--config_path", str(SAMPLE_CONFIG_PATH)), id="config_path"),
        pytest.param(("--config_value", get_config_json()), id="config_value"),
    ],
)
def server_params(request: tuple) -> StdioServerParameters:
    """Create server parameters for different config methods."""
    param_name, param_value = request.param
    return StdioServerParameters(
        command="python",
        args=["-m", "mcp_this", param_name, param_value],
    )


@pytest.mark.asyncio
async def test_list_tools(server_params: StdioServerParameters):
    """Test that tools are properly registered and can be listed."""
    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        assert tools.tools  # Check that the tools list is not empty
        tool_names = [t.name for t in tools.tools]
        assert "example-tool" in tool_names


@pytest.mark.asyncio
async def test_call_tool(server_params: StdioServerParameters):
    """Test that a tool can be called and returns expected results."""
    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("example-tool", {"name": "World"})
        assert result.content
        result_text = result.content[0].text
        assert "Hello, World!" in result_text


@pytest.mark.asyncio
async def test_tool_parameters(server_params: StdioServerParameters):
    """Test that tool parameters are correctly defined."""
    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        example_tool = next((t for t in tools.tools if t.name == "example-tool"), None)
        assert example_tool is not None
        assert example_tool.inputSchema is not None
        assert 'properties' in example_tool.inputSchema
        assert 'name' in example_tool.inputSchema['properties']
        # Parameter is optional (no 'required' list or it's not in that list)
        # In JSON Schema, required fields are listed in a 'required' array at the schema root
        if 'required' in example_tool.inputSchema:
            assert 'name' not in example_tool.inputSchema['required']
