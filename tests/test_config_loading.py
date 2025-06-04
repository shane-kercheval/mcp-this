"""Unit tests for configuration loading in mcp_server.py."""
import os
import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from mcp_this.mcp_server import (
    get_default_config_path,
    load_config,
    validate_config,
)


class TestGetDefaultToolsPath:
    """Test cases for the get_default_config_path function."""

    @patch("pathlib.Path.exists")
    def test_default_path_exists(self, mock_exists: MagicMock) -> None:
        """Test when default config exists."""
        # Setup the mock to indicate the file exists
        mock_exists.return_value = True

        # Call the function
        result = get_default_config_path()

        # Assert the result is not None and ends with the expected path
        assert result is not None
        assert str(result).endswith(os.path.join("configs", "default.yaml"))

    @patch("pathlib.Path.exists")
    def test_default_path_not_exists(self, mock_exists: MagicMock) -> None:
        """Test when default config doesn't exist."""
        # Setup the mock to indicate the file doesn't exist
        mock_exists.return_value = False

        # Call the function
        result = get_default_config_path()

        # Assert the result is None
        assert result is None


class TestLoadConfig:
    """Test cases for the load_config function."""

    def test_load_config_with_tools_json(self):
        """Test loading configuration from tools JSON string."""
        # Create a test JSON string
        tools_json = json.dumps({"tools": {"test": {"execution": {"command": "echo test"}}}})

        # Call the function
        result = load_config(tools=tools_json)

        # Assert the result is correct
        assert result == {"tools": {"test": {"execution": {"command": "echo test"}}}}

    def test_load_config_empty_json(self):
        """Test loading configuration with empty JSON."""
        # Create an empty JSON string
        tools_json = json.dumps({})

        # Assert that ValueError is raised
        with pytest.raises(ValueError, match="Configuration value is empty"):
            load_config(tools=tools_json)

    def test_load_config_invalid_json(self):
        """Test loading configuration with invalid JSON."""
        # Create an invalid JSON string
        tools_json = "{invalid: json}"

        # Assert that ValueError is raised
        with pytest.raises(ValueError, match="Error parsing JSON configuration"):
            load_config(tools=tools_json)

    @patch("builtins.open", new_callable=mock_open,
           read_data="tools:\n  test:\n    execution:\n      command: echo test")
    @patch("pathlib.Path.is_file")
    def test_load_config_with_config_path(self, mock_is_file: MagicMock, mock_file: MagicMock) -> None:  # noqa: E501
        """Test loading configuration from config_path."""
        # Setup the mock to indicate the file exists
        mock_is_file.return_value = True

        # Call the function
        result = load_config(config_path="/path/to/config.yaml")

        # Assert the result is correct
        assert result == {"tools": {"test": {"execution": {"command": "echo test"}}}}
        # Assert the file was opened correctly
        mock_file.assert_called_once_with(Path("/path/to/config.yaml"))

    @patch("pathlib.Path.is_file")
    def test_load_config_file_not_found(self, mock_is_file: MagicMock) -> None:
        """Test loading configuration with non-existent file."""
        # Setup the mock to indicate the file doesn't exist
        mock_is_file.return_value = False

        # Assert that FileNotFoundError is raised
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(config_path="/path/to/nonexistent.yaml")

    @patch("builtins.open", new_callable=mock_open, read_data="invalid: yaml: -")
    @patch("pathlib.Path.is_file")
    def test_load_config_invalid_yaml(self, mock_is_file: MagicMock, mock_file: MagicMock) -> None:  # noqa: ARG002
        """Test loading configuration with invalid YAML."""
        # Setup the mock to indicate the file exists
        mock_is_file.return_value = True

        # Mock yaml.safe_load to raise an exception
        with patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):  # noqa: SIM117
            # Assert that ValueError is raised
            with pytest.raises(ValueError, match="Error loading configuration"):
                load_config(config_path="/path/to/config.yaml")

    @patch("builtins.open", new_callable=mock_open, read_data="# Empty file")
    @patch("pathlib.Path.is_file")
    def test_load_config_empty_yaml(self, mock_is_file: MagicMock, mock_file: MagicMock) -> None:  # noqa: ARG002
        """Test loading configuration with empty YAML."""
        # Setup the mock to indicate the file exists
        mock_is_file.return_value = True

        # Mock yaml.safe_load to return None (empty YAML)
        with patch("yaml.safe_load", return_value=None):  # noqa: SIM117
            # Assert that ValueError is raised
            with pytest.raises(ValueError, match="Configuration file is empty"):
                load_config(config_path="/path/to/config.yaml")

    @patch.dict(os.environ, {"MCP_THIS_CONFIG_PATH": "/env/path/config.yaml"})
    @patch("pathlib.Path.is_file")
    @patch("builtins.open", new_callable=mock_open,
           read_data="tools:\n  test:\n    execution:\n      command: echo test")
    def test_load_config_from_env(self, mock_file: MagicMock, mock_is_file: MagicMock) -> None:
        """Test loading configuration from environment variable."""
        # Setup the mock to indicate the file exists
        mock_is_file.return_value = True

        # Call the function without specifying config_path or tools
        result = load_config()

        # Assert the result is correct
        assert result == {"tools": {"test": {"execution": {"command": "echo test"}}}}
        # Assert the file was opened correctly
        mock_file.assert_called_once_with(Path("/env/path/config.yaml"))

    @patch.dict(os.environ, {}, clear=True)  # Clear environment variables
    def test_load_config_from_default_real_file(self) -> None:
        """Test loading configuration from actual default config file."""
        import yaml
        from pathlib import Path

        # Find the actual default.yaml in the package
        package_dir = Path(__file__).parent.parent / "src" / "mcp_this"
        default_config_path = package_dir / "configs" / "default.yaml"

        # Skip if the file doesn't exist
        if not default_config_path.exists():
            pytest.skip("Default configuration file not found")

        # Temporarily patch get_default_config_path to return our known path
        with patch("mcp_this.mcp_server.get_default_config_path", return_value=default_config_path):  # noqa: E501
            # Call the function without specifying config_path or tools
            result = load_config()

            # Load the same file directly to compare
            with open(default_config_path) as f:
                expected = yaml.safe_load(f)

            # Compare the results
            assert result == expected
            assert "tools" in result, "Default config should contain tools section"

    @patch.dict(os.environ, {}, clear=True)  # Clear environment variables
    @patch("mcp_this.mcp_server.get_default_config_path")
    def test_load_config_no_config_found(self, mock_get_default: MagicMock) -> None:
        """Test loading configuration with no config sources."""
        # Setup the mock to indicate no default config
        mock_get_default.return_value = None

        # Assert that ValueError is raised
        with pytest.raises(ValueError, match="No configuration provided"):
            load_config()


class TestValidateConfig:
    """Test cases for the validate_config function."""

    def test_validate_config_not_dict(self):
        """Test validating a non-dictionary config."""
        # Assert that ValueError is raised
        with pytest.raises(ValueError, match="Configuration must be a dictionary"):
            validate_config([])

    def test_validate_config_missing_sections(self):
        """Test validating a config missing tools and prompts sections."""
        # Assert that ValueError is raised
        with pytest.raises(
            ValueError,
            match="Configuration must contain a 'tools' and/or 'prompts' section",
        ):
            validate_config({"other_section": {}})

    def test_validate_config_tools_not_dict(self):
        """Test validating a config with tools that's not a dictionary."""
        # Assert that ValueError is raised
        with pytest.raises(ValueError, match="'tools' must be a dictionary"):
            validate_config({"tools": []})

    def test_validate_config_tool_missing_execution(self):
        """Test validating a tool without an execution section."""
        # Assert that ValueError is raised
        with pytest.raises(ValueError, match="must contain an 'execution' section"):
            validate_config({
                "tools": {
                    "test": {"description": "Test tool"},
                },
            })

    def test_validate_config_tool_execution_not_dict(self):
        """Test validating a tool with execution that's not a dictionary."""
        # Assert that ValueError is raised
        with pytest.raises(ValueError, match="Execution section in .* must be a dictionary"):
            validate_config({
                "tools": {
                    "test": {
                        "description": "Test tool",
                        "execution": "echo test",
                    },
                },
            })

    def test_validate_config_tool_missing_command(self):
        """Test validating a tool without a command."""
        # Assert that ValueError is raised
        with pytest.raises(ValueError, match="execution must contain a 'command'"):
            validate_config({
                "tools": {
                    "test": {
                        "description": "Test tool",
                        "execution": {},
                    },
                },
            })


    def test_validate_config_valid_tools(self):
        """Test validating a valid config with tools."""
        # This should not raise an exception
        validate_config({
            "tools": {
                "test": {
                    "description": "Test tool",
                    "execution": {
                        "command": "echo test",
                    },
                },
            },
        })

