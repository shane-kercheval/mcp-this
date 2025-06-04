"""Tests for configuration file validation and loading."""
import tempfile
import pytest
import yaml
from pathlib import Path
from mcp_this.mcp_server import load_config, validate_config

class TestConfigurationFiles:
    """Test cases for configuration file handling."""

    def test_load_valid_config_file(self):
        """Test loading a valid configuration file."""
        # Create a valid configuration
        valid_config = {
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

        # Create a temporary file with the valid configuration
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as config_file:
            yaml.dump(valid_config, config_file)
            config_file.flush()

            # Load the configuration
            result = load_config(config_path=config_file.name)

            # Assert that the result matches the expected configuration
            assert result == valid_config

    def test_load_invalid_yaml_syntax(self):
        """Test loading a file with invalid YAML syntax."""
        # Create a temporary file with invalid YAML syntax
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as config_file:
            config_file.write("invalid: yaml: -\nindentation error")
            config_file.flush()

            # Assert that loading the configuration raises a ValueError
            with pytest.raises(ValueError, match="Error loading configuration"):
                load_config(config_path=config_file.name)


    def test_default_config_file_content(self):
        """Test the content of the default configuration file."""
        # Find the default config path
        package_dir = Path(__file__).parent.parent / "src" / "mcp_this"
        default_config_paths = [
            package_dir / "configs" / "default.yaml",
        ]

        # Find the first existing default config file
        default_config_path = None
        for path in default_config_paths:
            if path.exists():
                default_config_path = path
                break

        # Skip the test if no default config file is found
        if default_config_path is None:
            pytest.skip("Default configuration file not found")

        # Load the default configuration
        with open(default_config_path) as f:
            default_config = yaml.safe_load(f)

        # Validate the default configuration
        validate_config(default_config)

        # Check that the default configuration has the expected structure
        assert isinstance(default_config, dict)
        assert "tools" in default_config


    def test_config_with_empty_parameters(self):
        """Test configuration with empty parameters section."""
        # Create a configuration with an empty parameters section
        config = {
            "tools": {
                "echo": {
                    "description": "Echo tool",
                    "execution": {
                        "command": "echo test",
                    },
                    "parameters": {},
                },
            },
        }

        # Validate the configuration (should not raise an exception)
        validate_config(config)


    def test_combined_tools_and_config_validation(self):
        """Test combined validation of tools loaded from a config file."""
        # Create a valid configuration
        valid_config = {
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

        # Create a temporary file with the valid configuration
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as config_file:
            yaml.dump(valid_config, config_file)
            config_file.flush()

            # Load the configuration
            result = load_config(config_path=config_file.name)

            # Validate the loaded configuration
            validate_config(result)

            # Assert that the result matches the expected configuration
            assert result == valid_config
