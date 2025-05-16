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
            result = load_config(tools_path=config_file.name)

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
                load_config(tools_path=config_file.name)




    def test_default_config_file_content(self):
        """Test the content of the default configuration file."""
        # Find the default config path
        package_dir = Path(__file__).parent.parent / "src" / "mcp_this"
        default_config_paths = [
            package_dir / "configs" / "default.yaml",
            package_dir / "config" / "default.yaml",
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
        assert "tools" in default_config or "toolsets" in default_config

    def test_example_config_file_content(self):
        """Test the content of example configuration files."""
        # Find example config files
        example_configs_dir = Path(__file__).parent.parent / "examples"
        if not example_configs_dir.exists():
            pytest.skip("Examples directory not found")

        example_configs = list(example_configs_dir.glob("*.yaml"))

        # Skip the test if no example config files are found
        if not example_configs:
            pytest.skip("No example configuration files found")

        # Check each example config file
        for config_path in example_configs:
            # Load the example configuration
            with open(config_path) as f:
                example_config = yaml.safe_load(f)

            # Skip if the file doesn't contain a valid YAML dictionary
            if not isinstance(example_config, dict):
                continue

            # Validate the example configuration if it has tools or toolsets
            if "tools" in example_config or "toolsets" in example_config:
                validate_config(example_config)

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

    def test_config_with_uses_working_dir(self):
        """Test configuration with uses_working_dir option."""
        # Create a configuration with uses_working_dir option
        config = {
            "tools": {
                "ls": {
                    "description": "List files",
                    "execution": {
                        "command": "ls",
                        "uses_working_dir": True,
                    },
                    "parameters": {
                        "working_dir": {
                            "description": "Working directory",
                            "required": False,
                        },
                    },
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
            result = load_config(tools_path=config_file.name)

            # Validate the loaded configuration
            validate_config(result)

            # Assert that the result matches the expected configuration
            assert result == valid_config
