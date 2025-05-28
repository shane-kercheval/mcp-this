"""Unit tests for tool registration functions in mcp_server.py."""
from unittest.mock import patch, MagicMock
from mcp_this.mcp_server import (
    register_parsed_tools,
    register_tools,
    ToolInfo,
)
from mcp_this.tools import create_tool_info


class TestRegisterTools:
    """Test cases for the register_tools function."""

    @patch('mcp_this.mcp_server.parse_tools')
    @patch('mcp_this.mcp_server.register_parsed_tools')
    def test_register_tools(self, mock_register_parsed_tools: MagicMock,
                           mock_parse_tools: MagicMock) -> None:
        """Test that register_tools parses config and registers tools."""
        # Setup mock to return sample tools
        mock_tools = [MagicMock(spec=ToolInfo)]
        mock_parse_tools.return_value = mock_tools

        # Setup test config
        config = {"tools": {"test": {"execution": {"command": "echo test"}}}}

        # Call register_tools
        register_tools(config)

        # Assert parse_tools was called with the config
        mock_parse_tools.assert_called_once_with(config)
        # Assert register_parsed_tools was called with the tools from parse_tools
        mock_register_parsed_tools.assert_called_once_with(mock_tools)


class TestRegisterParsedTools:
    """Test cases for the register_parsed_tools function."""

    @patch('mcp_this.mcp_server.mcp')
    def test_register_parsed_tools_empty(self, mock_mcp: MagicMock) -> None:
        """Test register_parsed_tools with empty list."""
        # Call register_parsed_tools with empty list
        register_parsed_tools([])

        # Assert that mcp.tool was not called
        mock_mcp.tool.assert_not_called()

    @patch('mcp_this.mcp_server.mcp')
    def test_register_parsed_tools_single(self, mock_mcp: MagicMock) -> None:
        """Test register_parsed_tools with a single tool."""
        # Create a sample ToolInfo object
        tool_info = create_tool_info(
            tool_name="echo",
            tool_config={
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
        )

        # Setup mcp.tool to return a decorator function
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        # Call register_parsed_tools
        register_parsed_tools([tool_info])

        # Assert that mcp.tool was called with the correct arguments
        mock_mcp.tool.assert_called_once()
        args, kwargs = mock_mcp.tool.call_args
        assert kwargs["name"] == "echo"
        assert kwargs["description"] == tool_info.get_full_description()

        # Assert that the decorator function was called
        mock_decorator.assert_called_once()

    @patch('mcp_this.mcp_server.mcp')
    @patch('builtins.exec')
    def test_register_parsed_tools_exec_exception(self, mock_exec: MagicMock, mock_mcp: MagicMock) -> None:  # noqa: E501
        """Test register_parsed_tools with exception during exec."""
        # Create a sample ToolInfo object
        tool_info = MagicMock(spec=ToolInfo)
        tool_info.exec_code = "some invalid code"
        tool_info.function_name = "test_function"
        tool_info.tool_name = "test"
        tool_info.get_full_description.return_value = "Test description"

        # Make exec raise an exception
        mock_exec.side_effect = SyntaxError("Invalid syntax")

        # Call register_parsed_tools with print_exc patched
        with patch('traceback.print_exc') as mock_print_exc:
            register_parsed_tools([tool_info])

        # Assert that traceback.print_exc was called
        mock_print_exc.assert_called_once()
        # Assert that mcp.tool was not called
        mock_mcp.tool.assert_not_called()

    @patch('mcp_this.mcp_server.mcp')
    def test_register_parsed_tools_multiple(self, mock_mcp: MagicMock) -> None:
        """Test register_parsed_tools with multiple tools."""
        # Create sample ToolInfo objects
        tool_info1 = create_tool_info(
            tool_name="echo",
            tool_config={
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
        )
        tool_info2 = create_tool_info(
            tool_name="read",
            tool_config={
                "description": "Read file",
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
        )

        # Setup mcp.tool to return a decorator function
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        # Call register_parsed_tools
        register_parsed_tools([tool_info1, tool_info2])

        # Assert that mcp.tool was called twice
        assert mock_mcp.tool.call_count == 2
        # Assert that the decorator function was called twice
        assert mock_decorator.call_count == 2

        # Check calls for first tool
        args1, kwargs1 = mock_mcp.tool.call_args_list[0]
        assert kwargs1["name"] == "echo"
        assert kwargs1["description"] == tool_info1.get_full_description()

        # Check calls for second tool
        args2, kwargs2 = mock_mcp.tool.call_args_list[1]
        assert kwargs2["name"] == "read"
        assert kwargs2["description"] == tool_info2.get_full_description()


class TestToolRegistrationIntegration:
    """Integration tests for tool registration process."""

    @patch('mcp_this.mcp_server.mcp')
    def test_register_tools_from_config(self, mock_mcp: MagicMock) -> None:
        """Test end-to-end registration from config to mcp.tool."""
        # Setup test config
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
                "read": {
                    "description": "Read file",
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

        # Setup mcp.tool to return a decorator function
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        # Call register_tools
        register_tools(config)

        # Assert that mcp.tool was called twice
        assert mock_mcp.tool.call_count == 2
        # Assert that the decorator function was called twice
        assert mock_decorator.call_count == 2

        # Check that both tools were registered with correct names
        tool_names = [kwargs["name"] for _, kwargs in mock_mcp.tool.call_args_list]
        assert "echo" in tool_names
        assert "read" in tool_names
