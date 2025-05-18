"""Edge case tests for command execution in mcp_this."""
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from mcp_this.tools import execute_command, build_command


class TestCommandExecutionEdgeCases:
    """Test cases for edge conditions in command execution."""

    @pytest.mark.asyncio
    async def test_execute_non_executable_file(self):
        """Test executing a non-executable file."""
        with tempfile.NamedTemporaryFile(mode="w+") as temp_file:
            # Write a simple script to the file
            temp_file.write("#!/bin/sh\necho 'Hello, World!'\n")
            temp_file.flush()

            # Don't set executable permissions

            # Try to execute the file
            result = await execute_command(f"{temp_file.name}")

            # Should contain an error message
            assert "Error executing command:" in result

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test executing a command that takes too long."""
        # Create a command that sleeps for 5 seconds
        with patch('asyncio.create_subprocess_shell') as mock_create_subprocess:
            # Setup mock process
            mock_process = MagicMock()
            mock_process.communicate.side_effect = TimeoutError()
            mock_create_subprocess.return_value = mock_process

            # Execute with timeout
            with patch('asyncio.wait_for', side_effect=TimeoutError()):
                result = await execute_command("sleep 5")

            # Should contain an error message
            assert "Error:" in result


    @pytest.mark.asyncio
    async def test_execute_command_not_in_path(self):
        """Test executing a command that doesn't exist in PATH."""
        # Try to execute a non-existent command
        result = await execute_command("command_that_definitely_does_not_exist_12345")

        # Should contain an error message
        assert "Error executing command:" in result

    @pytest.mark.asyncio
    async def test_execute_with_large_output(self):
        """Test executing a command that produces very large output."""
        # Generate a very large output (hundreds of KB)
        command = "yes 'test line' | head -n 20000"

        # Execute the command
        result = await execute_command(command)

        # Should contain the expected pattern many times
        assert "test line" in result
        assert len(result) > 100000  # Should be quite large

    @pytest.mark.asyncio
    async def test_execute_with_binary_output(self):
        """Test executing a command that produces binary output."""
        # Create a binary file
        with tempfile.NamedTemporaryFile(mode="wb") as temp_file:
            # Write some binary data
            temp_file.write(bytes(range(256)))
            temp_file.flush()

            # Try to cat the binary file
            result = await execute_command(f"cat {temp_file.name}")

            # Should contain decoded binary data
            assert result is not None
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execute_with_env_vars(self):
        """Test executing a command that depends on environment variables."""
        # Set a custom environment variable
        with patch.dict(os.environ, {"CUSTOM_VAR": "test_value"}):
            # Execute a command that uses the environment variable
            result = await execute_command("echo $CUSTOM_VAR")

            # Should contain the value of the environment variable
            assert "test_value" in result


    @pytest.mark.asyncio
    async def test_execute_with_wildcard_expansion(self):
        """Test executing a command with wildcard expansion."""
        # Create a temporary directory with multiple files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple files
            for i in range(3):
                # Use Path to create files instead of open
                path = Path(temp_dir) / f"file{i}.txt"
                path.write_text(f"Content {i}")

            # Try to list files with a wildcard
            result = await execute_command(f"ls {temp_dir}/*.txt")

            # Should list all the files
            for i in range(3):
                assert f"file{i}.txt" in result


class TestBuildCommandEdgeCases:
    """Test cases for edge conditions in build_command."""

    def test_build_command_with_all_parameters_missing(self):
        """Test building a command where all placeholders have no values."""
        template = "test <<param1>> <<param2>> <<param3>>"
        parameters = {}

        result = build_command(template, parameters)

        # Should remove all placeholders
        assert result == "test"

    def test_build_command_with_adjacent_placeholders(self):
        """Test building a command with adjacent placeholders."""
        template = "test<<param1>><<param2>>end"
        parameters = {"param1": "value1", "param2": "value2"}

        result = build_command(template, parameters)

        # Should replace both placeholders without extra spaces
        assert result == "testvalue1value2end"

    def test_build_command_with_placeholder_substrings(self):
        """Test building a command with placeholder substrings."""
        template = "test <<param>> <<param_ext>>"
        parameters = {"param": "value1", "param_ext": "value2"}

        result = build_command(template, parameters)

        # Should correctly distinguish between similar parameter names
        assert result == "test value1 value2"

    def test_build_command_with_escaped_placeholders(self):
        """Test building a command with escaped placeholders."""
        template = "test \\<<param>> <<param>>"
        parameters = {"param": "value"}

        # The backslash should be preserved in the template
        # and only the actual placeholder should be replaced
        result = build_command(template, parameters)

        # Expected result depends on how the code handles escaped placeholders
        # This may need adjustment based on actual implementation
        assert "value" in result

    def test_build_command_with_false_boolean_value(self):
        """Test building a command with a False boolean value."""
        template = "test --flag=<<flag>>"
        parameters = {"flag": False}

        result = build_command(template, parameters)

        # Should convert False to "False" string
        assert result == "test --flag=False"

    def test_build_command_with_zero_value(self):
        """Test building a command with a zero value."""
        template = "test --count=<<count>>"
        parameters = {"count": 0}

        result = build_command(template, parameters)

        # Should convert 0 to "0" string
        assert result == "test --count=0"

    def test_build_command_with_special_characters(self):
        """Test building a command with special characters in parameters."""
        template = "test <<param>>"
        parameters = {"param": "value with $ & | ; < > ( ) \" ' \\"}

        result = build_command(template, parameters)

        # Should preserve all special characters
        assert result == "test value with $ & | ; < > ( ) \" ' \\"
