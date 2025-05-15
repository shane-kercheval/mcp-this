"""Unit tests for the MCP server."""
import pytest
import json
import yaml
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_this.mcp_server import build_command


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
class TestMCPServer:
    """Test cases for the MCP server."""

    async def test_list_tools(self, server_params: StdioServerParameters):
        """Test that tools are properly registered and can be listed."""
        async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:  # noqa: E501
            await session.initialize()
            tools = await session.list_tools()
            assert tools.tools  # Check that the tools list is not empty
            tool_names = [t.name for t in tools.tools]
            assert "example-tool" in tool_names


    @pytest.mark.asyncio
    async def test_call_tool(self, server_params: StdioServerParameters):
        """Test that a tool can be called and returns expected results."""
        async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:  # noqa: E501
            await session.initialize()
            result = await session.call_tool("example-tool", {"name": "World"})
            assert result.content
            result_text = result.content[0].text
            assert "Hello, World!" in result_text


    @pytest.mark.asyncio
    async def test_tool_parameters(self, server_params: StdioServerParameters):
        """Test that tool parameters are correctly defined."""
        async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:  # noqa: E501
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


class TestBuildCommand:
    """Test cases for the build_command function."""

    def test_simple_parameter_substitution(self):
        """Test basic parameter substitution."""
        template = "echo <<message>>"
        params = {"message": "Hello, World!"}
        result = build_command(template, params)
        assert result == "echo Hello, World!"

    def test_multiple_parameters(self):
        """Test substitution of multiple parameters."""
        template = "curl -X GET <<url>> -H 'Authorization: Bearer <<token>>'"
        params = {"url": "https://api.example.com", "token": "abc123"}
        result = build_command(template, params)
        assert result == "curl -X GET https://api.example.com -H 'Authorization: Bearer abc123'"

    def test_empty_parameters(self):
        """Test handling of empty parameter values."""
        template = "echo <<message>> <<suffix>>"
        params = {"message": "Hello", "suffix": ""}
        result = build_command(template, params)
        assert result == "echo Hello"

    def test_none_parameters(self):
        """Test handling of None parameter values."""
        template = "echo <<message>> <<suffix>>"
        params = {"message": "Hello", "suffix": None}
        result = build_command(template, params)
        assert result == "echo Hello"

    def test_numeric_parameters(self):
        """Test handling of numeric parameter values."""
        template = "tail -n <<lines>> <<file>>"
        params = {"lines": 10, "file": "/var/log/syslog"}
        result = build_command(template, params)
        assert result == "tail -n 10 /var/log/syslog"

    def test_missing_parameters(self):
        """Test handling of parameters missing from the dictionary."""
        template = "echo <<message>> <<missing>>"
        params = {"message": "Hello"}
        result = build_command(template, params)
        assert result == "echo Hello"

    def test_extra_parameters(self):
        """Test handling of extra parameters not used in template."""
        template = "echo <<message>>"
        params = {"message": "Hello", "unused": "World"}
        result = build_command(template, params)
        assert result == "echo Hello"

    def test_multiple_spaces(self):
        """Test normalization of multiple spaces."""
        template = "echo   <<message>>    <<suffix>>"
        params = {"message": "Hello", "suffix": "World"}
        result = build_command(template, params)
        assert result == "echo Hello World"

    def test_escaped_parameters(self):
        """Test handling of parameters with special characters that might need escaping."""
        template = "echo <<message>>"
        params = {"message": "Hello \"World\"!"}
        result = build_command(template, params)
        assert result == "echo Hello \"World\"!"

    def test_path_with_spaces(self):
        """Test handling of paths with spaces."""
        template = "cat <<file_path>>"
        params = {"file_path": "/path/to/my file.txt"}
        result = build_command(template, params)
        assert result == "cat /path/to/my file.txt"

    def test_empty_template(self):
        """Test handling of empty template."""
        template = ""
        params = {"message": "Hello"}
        result = build_command(template, params)
        assert result == ""

    def test_empty_params(self):
        """Test handling of empty parameters dictionary."""
        template = "echo <<message>> <<suffix>>"
        params = {}
        result = build_command(template, params)
        assert result == "echo"

    def test_multiple_instances_of_same_parameter(self):
        """Test handling of multiple instances of the same parameter."""
        template = "echo <<message>> and again <<message>>"
        params = {"message": "Hello"}
        result = build_command(template, params)
        assert result == "echo Hello and again Hello"

    def test_special_shell_characters(self):
        """Test handling of special shell characters in parameters."""
        template = "echo <<message>>"
        params = {"message": "Hello; rm -rf /"}
        result = build_command(template, params)
        assert result == "echo Hello; rm -rf /"
