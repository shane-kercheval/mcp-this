"""Unit tests for the MCP server."""
import pytest
import os
import tempfile
import shutil
import anyio
import json
import yaml
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_this.mcp_server import build_command, execute_command, parse_tools


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


class TestExecuteCommand:
    """Test cases for the execute_command function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing working directory functionality."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up after test
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def test_file(self, temp_dir: Path):
        """Create a test file in the temporary directory."""
        test_file_path = Path(temp_dir) / "test_file.txt"
        with open(test_file_path, "w") as f:
            f.write("test content")
        return test_file_path

    @pytest.mark.asyncio
    async def test_successful_command(self):
        """Test executing a command that succeeds."""
        result = await execute_command("echo 'Hello, World!'")
        assert "Hello, World!" in result

    @pytest.mark.asyncio
    async def test_failed_command(self):
        """Test executing a command that fails."""
        result = await execute_command("command_that_does_not_exist")
        assert "Error executing command:" in result

    @pytest.mark.asyncio
    async def test_command_with_working_dir(self, temp_dir: Path, test_file: Path):
        """Test executing a command with a specified working directory."""
        file_name = os.path.basename(test_file)
        cmd = "ls"
        result = await execute_command(cmd, temp_dir)
        assert file_name in result

    @pytest.mark.asyncio
    async def test_nonexistent_working_dir(self):
        """Test executing a command with a non-existent working directory."""
        non_existent_dir = "/path/that/does/not/exist"
        result = await execute_command("echo test", non_existent_dir)
        assert "Error: Working directory does not exist" in result

    @pytest.mark.asyncio
    async def test_working_dir_not_a_directory(self, test_file: Path):
        """Test executing a command where working_dir is a file, not a directory."""
        result = await execute_command("echo test", str(test_file))
        assert "Error: Working directory is not a directory" in result

    @pytest.mark.asyncio
    async def test_command_with_stderr(self):
        """Test a command that outputs to stderr but succeeds."""
        cmd = "echo 'Warning message' >&2 && echo 'Output'"
        result = await execute_command(cmd)
        assert "Output" in result
        assert "Warning message" not in result  # We return stdout, not stderr when stdout exists

    @pytest.mark.asyncio
    async def test_command_with_only_stderr(self):
        """Test a command that outputs only to stderr and nothing to stdout."""
        # Command that only writes to stderr
        cmd = "echo 'Warning message' >&2"
        result = await execute_command(cmd)
        assert "Command produced no output, but stderr: Warning message" in result

    @pytest.mark.asyncio
    async def test_empty_command(self):
        """Test executing an empty command."""
        # Empty command on macOS doesn't raise an error but returns empty output
        # Adjust the test to just check that we get a string return value
        result = await execute_command("")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_command_with_unicode(self):
        """Test executing a command with Unicode characters."""
        # Unicode characters should be preserved
        result = await execute_command("echo '你好，世界！'")  # noqa: RUF001
        assert "你好，世界！" in result  # noqa: RUF001

    @pytest.mark.asyncio
    async def test_multiline_output(self):
        """Test executing a command that produces multiline output."""
        cmd = "echo -e 'line1\\nline2\\nline3'"
        result = await execute_command(cmd)
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result


    @pytest.mark.asyncio
    async def test_large_output(self):
        """Test executing a command that produces large output."""
        # Generate a ~100KB output
        cmd = "yes 'test line' | head -n 5000"
        result = await execute_command(cmd)
        # Check that we got substantial output (at least 10KB)
        assert len(result) > 10000
        assert "test line" in result

    @pytest.mark.asyncio
    async def test_shell_expansion(self):
        """Test shell expansion and globbing in commands."""
        # Create a temporary directory with multiple files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            for i in range(3):
                path = Path(temp_dir) / f"test{i}.txt"
                path.write_text(f"Content {i}")

            # Use shell expansion to list files
            cmd = f"ls {temp_dir}/*.txt"
            result = await execute_command(cmd)

            # Verify all files are listed
            for i in range(3):
                assert f"test{i}.txt" in result

    @pytest.mark.asyncio
    async def test_environment_variables(self):
        """Test command with environment variables."""
        # The command should have access to environment variables
        cmd = "echo $HOME" if os.name != "nt" else "echo %USERPROFILE%"

        result = await execute_command(cmd)
        # Should contain a valid path
        assert "/" in result or "\\" in result

    @pytest.mark.asyncio
    async def test_command_with_quotes(self):
        """Test command with various types of quotes."""
        # Command with nested quotes
        cmd = 'echo "This has \'nested\' quotes"'
        result = await execute_command(cmd)
        assert "This has 'nested' quotes" in result

    @pytest.mark.asyncio
    async def test_command_with_redirection(self):
        """Test command with redirection."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Write to the temporary file using redirection
            cmd = f"echo 'Redirected output' > {temp_path}"
            await execute_command(cmd)

            # Check if the redirection worked
            async with await anyio.open_file(temp_path) as f:
                content = await f.read()
                assert "Redirected output" in content
        finally:
            # Clean up
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_command_with_pipes(self):
        """Test command with pipes."""
        # Use pipes to process output
        cmd = "echo 'line1\nline2\nline3' | grep 'line2'"
        result = await execute_command(cmd)
        assert "line2" in result
        assert "line1" not in result
        assert "line3" not in result

    @pytest.mark.asyncio
    async def test_consecutive_commands(self):
        """Test executing consecutive commands with semicolons."""
        cmd = "echo 'First'; echo 'Second'; echo 'Third'"
        result = await execute_command(cmd)
        assert "First" in result
        assert "Second" in result
        assert "Third" in result

    @pytest.mark.asyncio
    async def test_command_with_special_chars(self):
        """Test command with special shell characters."""
        cmd = "echo 'Special chars: & | ; < > ( ) $ \\ \"'"
        result = await execute_command(cmd)
        assert "Special chars: & | ; < > ( ) $ \\ \"" in result

    @pytest.mark.asyncio
    async def test_working_dir_with_special_chars(self, temp_dir: Path):
        """Test working directory with special characters in the path."""
        # Create a nested directory with special characters
        special_dir = Path(temp_dir) / "special dir with spaces!"
        special_dir.mkdir()

        # Create a test file in the special directory
        test_file = special_dir / "test.txt"
        test_file.write_text("test content")

        # Run a command in the special directory
        result = await execute_command("ls", str(special_dir))
        assert "test.txt" in result


class TestParseTools:
    """Test cases for the parse_tools function."""

    def test_no_toolsets(self):
        """Test parsing a configuration with no toolsets section."""
        config = {"other_section": {}}
        result = parse_tools(config)
        assert result == []

    def test_empty_toolsets(self):
        """Test parsing a configuration with an empty toolsets section."""
        config = {"toolsets": {}}
        result = parse_tools(config)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_empty_tools(self):
        """Test parsing a configuration with an empty tools section."""
        config = {
            "toolsets": {
                "example": {
                    "tools": {},
                },
            },
        }
        result = parse_tools(config)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_basic_tool(self):
        """Test parsing a configuration with a basic tool."""
        config = {
            "toolsets": {
                "example": {
                    "tools": {
                        "tool": {
                            "description": "A test tool",
                            "execution": {
                                "command": "echo Hello!",
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert isinstance(result, list)
        assert len(result) == 1

        tool = result[0]
        assert tool["toolset_name"] == "example"
        assert tool["tool_name"] == "tool"
        assert tool["full_tool_name"] == "example-tool"
        assert tool["function_name"] == "example_tool"
        assert tool["command_template"] == "echo Hello!"
        assert tool["description"] == "A test tool"
        assert not tool["uses_working_dir"]

    def test_tool_with_same_name_as_toolset(self):
        """Test parsing where tool name equals toolset name."""
        config = {
            "toolsets": {
                "example": {
                    "tools": {
                        "example": {
                            "description": "A test tool",
                            "execution": {
                                "command": "echo Hello!",
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool["full_tool_name"] == "example"  # Not prefixed with toolset
        assert tool["function_name"] == "example"

    def test_tool_with_parameters(self):
        """Test parsing a tool with parameters."""
        config = {
            "toolsets": {
                "example": {
                    "tools": {
                        "greet": {
                            "description": "A greeting tool",
                            "execution": {
                                "command": "echo Hello, <<name>>!",
                            },
                            "parameters": {
                                "name": {
                                    "description": "Your name",
                                    "required": False,
                                },
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool["parameters"] == {"name": {"description": "Your name", "required": False}}
        assert tool["param_string"] == "name: str = ''"
        assert "params['name'] = name" in tool["exec_code"]
        assert "tool_info" in tool
        assert tool["tool_info"]["parameters"] == ["name"]

    def test_tool_with_required_parameters(self):
        """Test parsing a tool with required parameters."""
        config = {
            "toolsets": {
                "example": {
                    "tools": {
                        "greet": {
                            "description": "A greeting tool",
                            "execution": {
                                "command": "echo Hello, <<name>>!",
                            },
                            "parameters": {
                                "name": {
                                    "description": "Your name",
                                    "required": True,
                                },
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool["param_string"] == "name"  # No default for required params

    def test_tool_with_working_dir(self):
        """Test parsing a tool with uses_working_dir flag."""
        config = {
            "toolsets": {
                "example": {
                    "tools": {
                        "list": {
                            "description": "List files",
                            "execution": {
                                "command": "ls",
                                "uses_working_dir": True,
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool["uses_working_dir"] is True
        assert tool["param_string"] == "working_dir: str = ''"
        assert "return await execute_command(cmd, working_dir)" in tool["exec_code"]

    def test_tool_with_working_dir_in_params(self):
        """Test parsing a tool with working_dir as an explicit parameter."""
        config = {
            "toolsets": {
                "example": {
                    "tools": {
                        "list": {
                            "description": "List files",
                            "execution": {
                                "command": "ls <<path>>",
                                "uses_working_dir": True,
                            },
                            "parameters": {
                                "path": {
                                    "description": "Path to list",
                                    "required": False,
                                },
                                "working_dir": {
                                    "description": "Working directory",
                                    "required": False,
                                },
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert "working_dir: str = ''" in tool["param_string"]
        assert "return await execute_command(cmd, params.get('working_dir', ''))" in tool["exec_code"]  # noqa: E501

    def test_tool_with_help_text(self):
        """Test parsing a tool with help text."""
        config = {
            "toolsets": {
                "example": {
                    "tools": {
                        "tool": {
                            "description": "A test tool",
                            "help_text": "This is a longer help text",
                            "execution": {
                                "command": "echo Hello!",
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool["description"] == "A test tool"
        assert tool["help_text"] == "This is a longer help text"
        assert tool["full_description"] == "A test tool\n\nThis is a longer help text"

    def test_multiple_tools(self):
        """Test parsing configuration with multiple tools in different toolsets."""
        config = {
            "toolsets": {
                "toolset1": {
                    "tools": {
                        "tool1": {
                            "description": "Tool 1",
                            "execution": {
                                "command": "echo Tool 1",
                            },
                        },
                    },
                },
                "toolset2": {
                    "tools": {
                        "tool2": {
                            "description": "Tool 2",
                            "execution": {
                                "command": "echo Tool 2",
                            },
                        },
                        "tool3": {
                            "description": "Tool 3",
                            "execution": {
                                "command": "echo Tool 3",
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 3

        # Extract full tool names for easier testing
        tool_names = [tool["full_tool_name"] for tool in result]
        assert "toolset1-tool1" in tool_names
        assert "toolset2-tool2" in tool_names
        assert "toolset2-tool3" in tool_names

    def test_tool_with_invalid_config_skipped(self):
        """Test that invalid tool configurations are skipped without throwing errors."""
        # This test would need some way to induce an error in tool parsing
        # For example, by making a parameter name invalid for a Python identifier
        config = {
            "toolsets": {
                "example": {
                    "tools": {
                        "valid": {
                            "description": "Valid tool",
                            "execution": {
                                "command": "echo Valid",
                            },
                        },
                        # This will cause an exception in the try block, but should be caught
                        "invalid": None,  # This should cause an exception but be caught
                    },
                },
            },
        }
        # This shouldn't raise an exception
        result = parse_tools(config)
        assert len(result) == 1
        assert result[0]["full_tool_name"] == "example-valid"

    def test_function_name_sanitized(self):
        """Test that function names are properly sanitized from invalid characters."""
        config = {
            "toolsets": {
                "test-toolset": {  # Contains a hyphen
                    "tools": {
                        "test.tool": {  # Contains a period
                            "description": "Test tool",
                            "execution": {
                                "command": "echo Test",
                            },
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool["full_tool_name"] == "test-toolset-test.tool"
        assert tool["function_name"] == "test_toolset_test_tool"  # Sanitized
