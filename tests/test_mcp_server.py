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
from mcp_this.mcp_server import (
    build_command,
    execute_command,
    parse_tools,
    ToolInfo,
    validate_config,
)


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
            assert "tool" in tool_names

    @pytest.mark.asyncio
    async def test_call_tool(self, server_params: StdioServerParameters):
        """Test that a tool can be called and returns expected results."""
        async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:  # noqa: E501
            await session.initialize()
            result = await session.call_tool("tool", {"name": "World"})
            assert result.content
            result_text = result.content[0].text
            assert "Hello, World!" in result_text

    @pytest.mark.asyncio
    async def test_tool_parameters(self, server_params: StdioServerParameters):
        """Test that tool parameters are correctly defined."""
        async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:  # noqa: E501
            await session.initialize()
            tools = await session.list_tools()
            example_tool = next((t for t in tools.tools if t.name == "tool"), None)
            assert example_tool is not None
            assert example_tool.inputSchema is not None
            assert 'properties' in example_tool.inputSchema
            assert 'name' in example_tool.inputSchema['properties']
            # Parameter is optional (no 'required' list or it's not in that list)
            # In JSON Schema, required fields are listed in a 'required' array at the schema root
            if 'required' in example_tool.inputSchema:
                assert 'name' not in example_tool.inputSchema['required']

    @pytest.mark.asyncio
    async def test_server_with_default_tools(self):
        """Test that the server starts with default tools."""
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_this"],
        )
        async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:  # noqa: E501
            await session.initialize()
            tools = await session.list_tools()
            assert tools.tools
            assert 'get-directory-tree' in [tool.name for tool in tools.tools]

    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test that prompts are properly registered and can be listed."""
        config_path = Path(__file__).parent / "fixtures" / "test_config_with_prompts.yaml"
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_this", "--config_path", str(config_path)],
        )
        async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:  # noqa: E501
            await session.initialize()
            prompts = await session.list_prompts()
            assert prompts.prompts  # Check that the prompts list is not empty
            prompt_names = [p.name for p in prompts.prompts]
            assert "test-prompt" in prompt_names

    @pytest.mark.asyncio
    async def test_get_prompt(self):
        """Test that a prompt can be retrieved and returns expected content."""
        config_path = Path(__file__).parent / "fixtures" / "test_config_with_prompts.yaml"
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_this", "--config_path", str(config_path)],
        )
        async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:  # noqa: E501
            await session.initialize()
            # Test getting a prompt with arguments
            result = await session.get_prompt(
                "test-prompt", {"subject": "testing", "details": "with details"},
            )
            assert result.messages
            content = result.messages[0].content.text
            assert "This is a test prompt for testing." in content
            assert "Additional details: with details" in content

    @pytest.mark.asyncio
    async def test_get_prompt_with_optional_args(self):
        """Test getting a prompt template with both required and optional arguments."""
        config_path = Path(__file__).parent / "fixtures" / "test_config_with_prompts.yaml"
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_this", "--config_path", str(config_path)],
        )
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Test prompt with both required and optional arguments
            result = await session.get_prompt(
                "test-prompt",
                {"subject": "testing", "details": "with details"},
            )

            assert result.messages
            message = result.messages[0]
            content = message.content.text

            # Check that both arguments were rendered
            assert "testing" in content
            assert "with details" in content

    @pytest.mark.asyncio
    async def test_get_prompt_without_optional_args(self):
        """Test getting a prompt template with only required arguments."""
        config_path = Path(__file__).parent / "fixtures" / "test_config_with_prompts.yaml"
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_this", "--config_path", str(config_path)],
        )
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Test prompt with only required argument
            result = await session.get_prompt(
                "test-prompt",
                {"subject": "testing"},
            )

            assert result.messages
            message = result.messages[0]
            content = message.content.text

            # Check that required argument was rendered
            assert "testing" in content
            # Optional content should not appear when not provided
            assert "Additional details:" not in content or "with details" not in content


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


class TestParseTools:
    """Test cases for the parse_tools function."""

    def test_no_tools(self):
        """Test parsing a configuration with no tools section."""
        config = {"other_section": {}}
        result = parse_tools(config)
        assert result == []

    def test_empty_tools(self):
        """Test parsing a configuration with an empty tools section."""
        config = {"tools": {}}
        result = parse_tools(config)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_tools_parsing(self):
        """Test parsing a configuration with tools."""
        config = {
            "tools": {
                "echo": {
                    "description": "Echo tool",
                    "execution": {
                        "command": "echo <<message>>",
                    },
                    "parameters": {
                        "message": {
                            "description": "Message to echo",
                            "required": True,
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert isinstance(result, list)
        assert len(result) == 1

        tool = result[0]
        assert isinstance(tool, ToolInfo)
        assert tool.tool_name == "echo"
        assert tool.function_name == "echo"
        assert tool.command_template == "echo <<message>>"
        assert tool.description == "Echo tool"

    def test_multiple_tools(self):
        """Test parsing a configuration with multiple tools."""
        config = {
            "tools": {
                "echo": {
                    "description": "Echo tool",
                    "execution": {
                        "command": "echo <<message>>",
                    },
                    "parameters": {
                        "message": {
                            "description": "Message to echo",
                            "required": True,
                        },
                    },
                },
                "cat": {
                    "description": "Cat file contents",
                    "execution": {
                        "command": "cat <<file_path>>",
                    },
                    "parameters": {
                        "file_path": {
                            "description": "Path to file",
                            "required": True,
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert isinstance(result, list)
        assert len(result) == 2

        # Extract tool names for easier testing
        tool_names = [tool.tool_name for tool in result]
        assert "echo" in tool_names
        assert "cat" in tool_names

        # Check the echo tool
        echo_tool = next(tool for tool in result if tool.tool_name == "echo")
        assert echo_tool.tool_name == "echo"
        assert echo_tool.command_template == "echo <<message>>"

        # Check the cat tool
        cat_tool = next(tool for tool in result if tool.tool_name == "cat")
        assert cat_tool.tool_name == "cat"
        assert cat_tool.command_template == "cat <<file_path>>"

    def test_basic_tool(self):
        """Test parsing a configuration with a basic tool."""
        config = {
            "tools": {
                "tool": {
                    "description": "A test tool",
                    "execution": {
                        "command": "echo Hello!",
                    },
                },
            },
        }
        result = parse_tools(config)
        assert isinstance(result, list)
        assert len(result) == 1

        tool = result[0]
        assert isinstance(tool, ToolInfo)
        assert tool.tool_name == "tool"
        assert tool.function_name == "tool"
        assert tool.command_template == "echo Hello!"
        assert tool.description == "A test tool"

    def test_tool_with_parameters(self):
        """Test parsing a tool with parameters."""
        config = {
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
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool.parameters == {"name": {"description": "Your name", "required": False}}
        assert tool.param_string == "name: str = ''"
        assert "params['name'] = name" in tool.exec_code
        assert "command_template" in tool.runtime_info
        assert tool.runtime_info["parameters"] == ["name"]

    def test_tool_with_required_parameters(self):
        """Test parsing a tool with required parameters."""
        config = {
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
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool.param_string == "name"  # No default for required params

    def test_multiple_different_tools(self):
        """Test parsing configuration with multiple different tools."""
        config = {
            "tools": {
                "tool1": {
                    "description": "Tool 1",
                    "execution": {
                        "command": "echo Tool 1",
                    },
                },
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
        }
        result = parse_tools(config)
        assert len(result) == 3

        # Extract tool names for easier testing
        tool_names = [tool.tool_name for tool in result]
        assert "tool1" in tool_names
        assert "tool2" in tool_names
        assert "tool3" in tool_names

    def test_tool_with_invalid_config_skipped(self):
        """Test that invalid tool configurations are skipped without throwing errors."""
        # This test would need some way to induce an error in tool parsing
        # For example, by making a parameter name invalid for a Python identifier
        config = {
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
        }
        # This shouldn't raise an exception
        result = parse_tools(config)
        assert len(result) == 1
        assert result[0].tool_name == "valid"

    def test_function_name_sanitized(self):
        """Test that function names are properly sanitized from invalid characters."""
        config = {
            "tools": {
                "test.tool": {  # Contains a period
                    "description": "Test tool",
                    "execution": {
                        "command": "echo Test",
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1
        tool = result[0]
        assert tool.tool_name == "test.tool"
        assert tool.function_name == "test_tool"  # Sanitized

    def test_get_full_description_basic(self):
        """Test get_full_description for a tool with no parameters."""
        config = {
            "tools": {
                "simple": {
                    "description": "A simple test tool",
                    "execution": {
                        "command": "echo Test",
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1

        tool = result[0]
        desc = tool.get_full_description()
        assert "Tool Description" in desc
        assert "A simple test tool" in desc
        assert "Underlying Command Called" in desc
        assert "```\necho Test\n```" in desc

    def test_get_full_description_with_parameters(self):
        """Test get_full_description for a tool with parameters."""
        config = {
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
                        "greeting": {
                            "description": "Greeting to use",
                            "required": True,
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1

        tool = result[0]
        desc = tool.get_full_description()
        assert "Tool Description" in desc
        assert "A greeting tool" in desc
        assert "Underlying Command Called" in desc
        assert "```\necho Hello, <<name>>!\n```" in desc
        assert "Parameters" in desc
        assert "- `name` [OPTIONAL] (string): Your name" in desc
        assert "- `greeting` [REQUIRED] (string): Greeting to use" in desc
        assert "EXAMPLE USAGE:" not in desc

    def test_get_full_description_with_complex_command(self):
        """Test get_full_description with a complex command template."""
        config = {
            "tools": {
                "find": {
                    "description": "Find files with pattern",
                    "execution": {
                        "command": "find . -name \"<<pattern>>\" -type f | xargs grep \"<<content>>\"",  # noqa: E501
                    },
                    "parameters": {
                        "pattern": {
                            "description": "File pattern to search for",
                            "required": True,
                        },
                        "content": {
                            "description": "Content to find in files",
                            "required": True,
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1

        tool = result[0]
        desc = tool.get_full_description()
        assert "Tool Description" in desc
        assert "Find files with pattern" in desc
        assert "Underlying Command Called" in desc
        assert "```\nfind . -name \"<<pattern>>\" -type f | xargs grep \"<<content>>\"\n```" in desc  # noqa: E501
        assert "Parameters" in desc
        assert "- `pattern` [REQUIRED] (string): File pattern to search for" in desc
        assert "- `content` [REQUIRED] (string): Content to find in files" in desc
        assert "EXAMPLE USAGE:" not in desc

    def test_parameter_type_inference(self):
        """Test that the get_full_description method correctly infers parameter types."""
        config = {
            "tools": {
                "process": {
                    "description": "Process files with given settings",
                    "execution": {
                        "command": "process --input=<<file_path>> --pattern=<<search_pattern>> --name=<<user_name>>",  # noqa: E501
                    },
                    "parameters": {
                        "file_path": {
                            "description": "Path to the input file",
                            "required": True,
                        },
                        "search_pattern": {
                            "description": "Pattern to search for",
                            "required": True,
                        },
                        "user_name": {
                            "description": "User name for processing",
                            "required": False,
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        assert len(result) == 1

        tool = result[0]
        desc = tool.get_full_description()

        # Check for parameter type
        assert "(string)" in desc

        # Check for placeholder example

        # Verify the section headers
        assert "Tool Description" in desc
        assert "Underlying Command Called" in desc
        assert "Parameters" in desc

        # Verify that EXAMPLE USAGE is not present
        assert "EXAMPLE USAGE:" not in desc

    def test_get_full_description_empty_parameter_description(self):
        """Test get_full_description with empty parameter descriptions."""
        config = {
            "tools": {
                "test": {
                    "description": "Test tool",
                    "execution": {
                        "command": "echo <<param1>> <<param2>>",
                    },
                    "parameters": {
                        "param1": {
                            "description": "",
                            "required": True,
                        },
                        "param2": {
                            "description": "Has description",
                            "required": False,
                        },
                    },
                },
            },
        }
        result = parse_tools(config)
        desc = result[0].get_full_description()

        # Should have PARAMETERS section
        assert "Parameters" in desc
        # Empty description should not have trailing colon
        assert "- `param1` [REQUIRED] (string)\n" in desc
        # Non-empty description should have colon
        assert "- `param2` [OPTIONAL] (string): Has description" in desc

    def test_get_full_description_no_parameters(self):
        """Test get_full_description with no parameters at all."""
        config = {
            "tools": {
                "simple": {
                    "description": "Simple tool with no params",
                    "execution": {
                        "command": "ls -la",
                    },
                },
            },
        }
        result = parse_tools(config)
        desc = result[0].get_full_description()

        # Should have description and command
        assert "Tool Description" in desc
        assert "Simple tool with no params" in desc
        assert "Underlying Command Called" in desc
        assert "```\nls -la\n```" in desc
        # Should NOT have PARAMETERS section
        assert "Parameters" not in desc
        # Should NOT have placeholder explanation
        assert "Text like <<parameter_name>>" not in desc

    def test_get_full_description_empty_tool_description(self):
        """Test get_full_description with empty tool description."""
        config = {
            "tools": {
                "test": {
                    "description": "",
                    "execution": {
                        "command": "echo test",
                    },
                },
            },
        }
        result = parse_tools(config)
        desc = result[0].get_full_description()

        # Should still have structure even with empty description
        assert "Tool Description" in desc
        assert "Underlying Command Called" in desc
        assert "```\necho test\n```" in desc


class TestValidateConfig:
    """Test cases for the validate_config function."""

    def test_validate_top_level_tools(self):
        """Test validating a config with top-level tools."""
        # Valid config with top-level tools
        valid_config = {
            "tools": {
                "echo": {
                    "description": "Echo tool",
                    "execution": {
                        "command": "echo Hello",
                    },
                },
            },
        }
        # This should not raise an exception
        validate_config(valid_config)

    def test_validate_missing_tools(self):
        """Test validating a config with no tools."""
        invalid_config = {
            "other_section": {},
        }
        with pytest.raises(
            ValueError, match="Configuration must contain a 'tools' and/or 'prompts' section",
        ):
            validate_config(invalid_config)

    def test_validate_invalid_tool_config(self):
        """Test validating a config with invalid tool configuration."""
        # Missing execution section
        invalid_config = {
            "tools": {
                "echo": {
                    "description": "Echo tool",
                },
            },
        }
        with pytest.raises(ValueError, match="must contain an 'execution' section"):
            validate_config(invalid_config)

        # Missing command in execution
        invalid_config = {
            "tools": {
                "echo": {
                    "description": "Echo tool",
                    "execution": {},
                },
            },
        }
        with pytest.raises(ValueError, match="execution must contain a 'command'"):
            validate_config(invalid_config)

    def test_validate_tools_config(self):
        """Test validating a config with tools."""
        valid_config = {
            "tools": {
                "echo": {
                    "description": "Echo tool",
                    "execution": {
                        "command": "echo Hello",
                    },
                },
                "cat": {
                    "description": "Cat file",
                    "execution": {
                        "command": "cat file.txt",
                    },
                },
            },
        }
        # This should not raise an exception
        validate_config(valid_config)
