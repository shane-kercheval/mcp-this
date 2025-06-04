"""Unit tests for the __main__ module."""
import os
from unittest.mock import patch
from mcp_this.__main__ import main

class TestFindDefaultConfig:
    """Test cases for the find_default_config function."""



class TestMain:
    """Test cases for the main function."""

    @patch('mcp_this.__main__.init_server')
    @patch('mcp_this.__main__.mcp')
    @patch('sys.argv', ['mcp-this', '--config-path', '/path/to/config.yaml'])
    def test_main_with_config_path(self, mock_mcp, mock_init_server):  # noqa: ANN001
        """Test main function with config-path argument."""
        # Run the main function
        main()

        # Check that init_server was called with the correct arguments
        mock_init_server.assert_called_once_with(config_path='/path/to/config.yaml', tools=None)
        # Check that mcp.run was called
        mock_mcp.run.assert_called_once_with(transport='stdio')

    @patch('mcp_this.__main__.init_server')
    @patch('mcp_this.__main__.mcp')
    @patch('sys.argv', ['mcp-this', '--config-value', '{"tools": {}}'])
    def test_main_with_tools_json(self, mock_mcp, mock_init_server):  # noqa: ANN001
        """Test main function with config-value JSON argument."""
        # Run the main function
        main()

        # Check that init_server was called with the correct arguments
        mock_init_server.assert_called_once_with(config_path=None, tools='{"tools": {}}')
        # Check that mcp.run was called
        mock_mcp.run.assert_called_once_with(transport='stdio')

    @patch('mcp_this.__main__.init_server')
    @patch('mcp_this.__main__.mcp')
    @patch('sys.argv', ['mcp-this'])
    @patch.dict(os.environ, {'MCP_THIS_CONFIG_PATH': '/env/path/config.yaml'})
    def test_main_with_env_var(self, mock_mcp, mock_init_server):  # noqa: ANN001
        """Test main function with environment variable."""
        # Run the main function
        main()

        # Check that init_server was called with the correct arguments
        mock_init_server.assert_called_once_with(config_path='/env/path/config.yaml', tools=None)
        # Check that mcp.run was called
        mock_mcp.run.assert_called_once_with(transport='stdio')

    @patch('mcp_this.__main__.find_default_config')
    @patch('mcp_this.__main__.init_server')
    @patch('mcp_this.__main__.mcp')
    @patch('sys.argv', ['mcp-this'])
    @patch.dict(os.environ, {}, clear=True)  # Clear environment variables
    def test_main_with_default_config(self, mock_mcp, mock_init_server, mock_find_default_config):  # noqa: ANN001
        """Test main function with default config."""
        # Mock find_default_config to return a path
        mock_find_default_config.return_value = '/default/config.yaml'

        # Run the main function
        main()

        # Check that init_server was called with the correct arguments
        mock_init_server.assert_called_once_with(config_path='/default/config.yaml', tools=None)
        # Check that mcp.run was called
        mock_mcp.run.assert_called_once_with(transport='stdio')


    @patch('mcp_this.__main__.init_server')
    @patch('mcp_this.__main__.mcp')
    @patch('sys.argv', ['mcp-this', '--transport', 'sse', '--config-path', '/path/to/config.yaml'])
    def test_main_custom_transport(self, mock_mcp, mock_init_server):  # noqa: ANN001
        """Test main function with custom transport."""
        # Run the main function
        main()

        # Check that init_server was called with the correct arguments
        mock_init_server.assert_called_once_with(config_path='/path/to/config.yaml', tools=None)
        # Check that mcp.run was called with the custom transport
        mock_mcp.run.assert_called_once_with(transport='sse')

    @patch('mcp_this.__main__.init_server')
    @patch('sys.argv', ['mcp-this', '--config-path', '/path/to/config.yaml'])
    @patch('sys.exit')
    def test_main_init_server_error(self, mock_exit, mock_init_server):  # noqa: ANN001
        """Test main function handling init_server errors."""
        # Mock init_server to raise an exception
        mock_init_server.side_effect = ValueError("Invalid config format")

        # Call main() and capture stderr
        with patch('sys.stderr'):
            main()

        # Check that sys.exit was called with code 1
        mock_exit.assert_called_once_with(1)

