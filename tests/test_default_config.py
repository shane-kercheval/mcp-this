"""Unit tests for the default configuration tools."""
import pytest
import tempfile
import os
import shutil
import re
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture
def server_params() -> StdioServerParameters:
    """Create server parameters with default configuration."""
    return StdioServerParameters(
        command="python",
        args=["-m", "mcp_this"],  # No need to specify config path for default config
    )


@pytest.fixture
def temp_test_directory():
    """Create a temporary directory with a test structure."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a test directory structure
        test_files = [
            "file1.txt",
            "file2.py",
            "subfolder1/file3.txt",
            "subfolder1/file4.py",
            "subfolder1/deeper/file5.txt",
            "subfolder2/file6.py",
            ".hidden_file",
            ".hidden_folder/hidden_file.txt",
        ]

        # Create files
        for file_path in test_files:
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(f"Content of {file_path}")

        # Create a .gitignore file
        with open(os.path.join(temp_dir, ".gitignore"), "w") as f:
            f.write("*.pyc\n")
            f.write("__pycache__/\n")
            f.write("subfolder2/\n")  # Ignore subfolder2

        # Create a file that should be ignored by .gitignore
        ignored_file = os.path.join(temp_dir, "ignored_file.pyc")
        with open(ignored_file, "w") as f:
            f.write("This file should be ignored by .gitignore")

        # Create a file in subfolder2 (should be ignored by .gitignore)
        ignored_by_gitignore = os.path.join(temp_dir, "subfolder2/ignored.txt")
        with open(ignored_by_gitignore, "w") as f:
            f.write("This file should be ignored by .gitignore")

        yield temp_dir
    finally:
        # Clean up
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
class TestGetDirectoryTree:
    """Test the get-directory-tree tool from the default configuration."""

    async def test_tool_registration(
        self, server_params: StdioServerParameters,
    ):
        """Test that the get-directory-tree tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "get-directory-tree" in tool_names

            # Get the tool details
            dir_tree_tool = next(t for t in tools.tools if t.name == "get-directory-tree")

            # Check tool schema has the expected parameters
            assert "directory" in dir_tree_tool.inputSchema["properties"]
            assert "custom_excludes" in dir_tree_tool.inputSchema["properties"]
            assert "format_args" in dir_tree_tool.inputSchema["properties"]

            # Verify only 'directory' is required
            assert "required" in dir_tree_tool.inputSchema
            assert "directory" in dir_tree_tool.inputSchema["required"]
            assert "custom_excludes" not in dir_tree_tool.inputSchema["required"]
            assert "format_args" not in dir_tree_tool.inputSchema["required"]

    async def test_basic_directory_tree(
            self,
            server_params: StdioServerParameters,
            temp_test_directory: str,
        ):
        """Test the get-directory-tree tool with basic usage."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with the test directory
            result = await session.call_tool(
                "get-directory-tree",
                {"directory": temp_test_directory},
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the result contains expected files and directories
            assert "file1.txt" in result_text
            assert "file2.py" in result_text
            assert "subfolder1" in result_text
            assert ".hidden_file" in result_text  # Hidden files are shown with -a
            assert ".hidden_folder" in result_text

            # Check that gitignore is respected
            assert "ignored_file.pyc" not in result_text  # Should be ignored by .gitignore
            assert "subfolder2/ignored.txt" not in result_text  # Should be ignored by .gitignore

    async def test_with_custom_excludes(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the get-directory-tree tool with custom excludes."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with custom excludes parameter
            result = await session.call_tool(
                "get-directory-tree",
                {
                    "directory": temp_test_directory,
                    # Exclude all .txt files and hidden files/dirs
                    "custom_excludes": "|*.txt|.hidden*",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that .txt files are excluded
            assert "file1.txt" not in result_text
            assert "file3.txt" not in result_text
            assert "file5.txt" not in result_text

            # Check that Python files are still included
            assert "file2.py" in result_text
            assert "file4.py" in result_text

            # Check that hidden files are excluded
            assert ".hidden_file" not in result_text
            assert ".hidden_folder" not in result_text

            # .gitignore exclusions should still be applied
            assert "ignored_file.pyc" not in result_text
            assert "subfolder2" not in result_text

    async def test_with_format_args(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the get-directory-tree tool with format arguments."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with format_args parameter to limit depth
            result = await session.call_tool(
                "get-directory-tree",
                {
                    "directory": temp_test_directory,
                    "format_args": "-L 1",  # Limit to depth 1 (no subdirectories contents)
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Root level files should be visible
            assert "file1.txt" in result_text
            assert "file2.py" in result_text

            # Folders should be visible but not their contents
            assert "subfolder1" in result_text

            # Check that deeper files are not shown due to depth limit
            assert "file3.txt" not in result_text
            assert "file4.py" not in result_text
            assert "file5.txt" not in result_text

            # Check directories-first formatting
            result2 = await session.call_tool(
                "get-directory-tree",
                {
                    "directory": temp_test_directory,
                    "format_args": "--dirsfirst",  # List directories before files
                },
            )
            result2_text = result2.content[0].text

            # Check if directories are listed before files
            # This is harder to test directly, but we can check that the output differs
            assert result2_text != result_text

            # Check pattern with regex to see if directories appear before files
            # This regex searches for the first file and directory and checks their order
            dir_pattern = r"(?:[^\n]*?)subfolder1[^\n]*?\n"
            file_pattern = r"(?:[^\n]*?)file1\.txt[^\n]*?\n"

            # Find first match position for directory and file
            dir_match = re.search(dir_pattern, result2_text)
            file_match = re.search(file_pattern, result2_text)

            # If both patterns are found, check that directory comes before file
            if dir_match and file_match:
                assert dir_match.start() < file_match.start()

    async def test_non_existent_directory(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the get-directory-tree tool with a non-existent directory."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with a non-existent directory
            result = await session.call_tool(
                "get-directory-tree",
                {"directory": "/path/that/doesnt/exist"},
            )

            # Verify we get some content
            assert result.content
            result_text = result.content[0].text
            # Just check that we received some output, as the specific error message
            # might vary depending on the environment
            assert len(result_text) > 0

    async def test_with_all_parameters(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the get-directory-tree tool with all parameters specified."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with all parameters
            result = await session.call_tool(
                "get-directory-tree",
                {
                    "directory": temp_test_directory,
                    "custom_excludes": "|*.py",  # Exclude Python files
                    "format_args": "-L 2 --dirsfirst",  # Limit depth and list dirs first
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that Python files are excluded
            assert "file2.py" not in result_text
            assert "file4.py" not in result_text
            assert "file6.py" not in result_text

            # But text files should be included
            assert "file1.txt" in result_text
            assert "file3.txt" in result_text

            # Check depth limitation - deeper structure should not be visible
            assert "deeper" in result_text  # Level 2 folder is visible
            assert "file5.txt" not in result_text  # Level 3 content is not visible

            # Check if directories are listed before files
            # Extract just the directory listing part (after the first line)
            tree_listing = result_text.split("\n", 1)[1] if "\n" in result_text else result_text

            # Find first match position for directory and file in the tree listing
            dir_pattern = r"(?:[^\n]*?)subfolder1[^\n]*?\n"
            file_pattern = r"(?:[^\n]*?)file1\.txt[^\n]*?\n"

            dir_match = re.search(dir_pattern, tree_listing)
            file_match = re.search(file_pattern, tree_listing)

            # If both patterns are found, check that directory comes before file
            if dir_match and file_match:
                assert dir_match.start() < file_match.start()

    async def test_directory_with_spaces(self, server_params: StdioServerParameters):
        """Test the get-directory-tree tool with a directory path containing spaces."""
        # Create a temporary directory with spaces in the name
        temp_dir_with_spaces = tempfile.mkdtemp(prefix="test dir with spaces ")
        try:
            # Create a simple file structure
            test_file = os.path.join(temp_dir_with_spaces, "test file.txt")
            with open(test_file, "w") as f:  # noqa: ASYNC230
                f.write("Test content")

            # Create a subfolder with spaces
            subfolder = os.path.join(temp_dir_with_spaces, "sub folder")
            os.makedirs(subfolder, exist_ok=True)
            with open(os.path.join(subfolder, "nested file.txt"), "w") as f:  # noqa: ASYNC230
                f.write("Nested content")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                # Call the tool with the directory containing spaces
                result = await session.call_tool(
                    "get-directory-tree",
                    {"directory": temp_dir_with_spaces},
                )

                # Verify we got some output
                assert result.content
                result_text = result.content[0].text

                # Check that files and folders with spaces are shown correctly
                assert "test file.txt" in result_text
                assert "sub folder" in result_text
                assert "nested file.txt" in result_text
        finally:
            # Clean up
            shutil.rmtree(temp_dir_with_spaces)

    async def test_empty_directory(self, server_params: StdioServerParameters):
        """Test the get-directory-tree tool with an empty directory."""
        # Create an empty temporary directory
        empty_dir = tempfile.mkdtemp()
        try:
            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                # Call the tool with the empty directory
                result = await session.call_tool(
                    "get-directory-tree",
                    {"directory": empty_dir},
                )

                # Verify we got some output
                assert result.content
                result_text = result.content[0].text

                # The output should show the directory with no contents (just a few lines)
                line_count = len(result_text.strip().split("\n"))
                assert 1 <= line_count <= 5, (
                    f"Expected 1-5 lines for empty directory, got {line_count}"
                )

                # The directory name should be in the output
                dir_name = os.path.basename(empty_dir)
                assert dir_name in result_text
        finally:
            # Clean up
            shutil.rmtree(empty_dir)


@pytest.mark.asyncio
class TestFindFiles:
    """Test the find-files tool from the default configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the find-files tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "find-files" in tool_names

            # Get the tool details
            find_files_tool = next(t for t in tools.tools if t.name == "find-files")

            # Check tool schema has the expected parameters
            assert "directory" in find_files_tool.inputSchema["properties"]
            assert "arguments" in find_files_tool.inputSchema["properties"]

            # Verify only 'directory' is required
            assert "required" in find_files_tool.inputSchema
            assert "directory" in find_files_tool.inputSchema["required"]
            assert "arguments" not in find_files_tool.inputSchema["required"]

    async def test_basic_file_finding(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-files tool with basic usage."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with the test directory to find all files
            result = await session.call_tool(
                "find-files",
                {"directory": temp_test_directory},
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the result contains expected files
            assert "file1.txt" in result_text
            assert "file2.py" in result_text
            assert "subfolder1/file3.txt" in result_text
            assert "subfolder1/file4.py" in result_text

            # Check that hidden files are also found
            assert ".hidden_file" in result_text

    async def test_find_by_extension(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-files tool with specific file extension filter."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to find only Python files
            result = await session.call_tool(
                "find-files",
                {
                    "directory": temp_test_directory,
                    "arguments": "-name '*.py'",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that only Python files are found
            assert "file2.py" in result_text
            assert "subfolder1/file4.py" in result_text

            # Check that non-Python files are not in the results
            assert "file1.txt" not in result_text
            assert "subfolder1/file3.txt" not in result_text
            assert ".hidden_file" not in result_text

    async def test_find_newer_files(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the find-files tool with timestamp filter."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        try:
            # Create an old file (modify time set to 2 days ago)
            old_file = os.path.join(temp_dir, "old_file.txt")
            with open(old_file, "w") as f:  # noqa: ASYNC230
                f.write("Old content")

            # Set its modification time to 2 days ago
            old_time = time.time() - (2 * 24 * 60 * 60)
            os.utime(old_file, (old_time, old_time))

            # Create a new file
            new_file = os.path.join(temp_dir, "new_file.txt")
            with open(new_file, "w") as f:  # noqa: ASYNC230
                f.write("New content")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                # Call the tool to find files newer than 1 day
                result = await session.call_tool(
                    "find-files",
                    {
                        "directory": temp_dir,
                        "arguments": "-mtime -1",
                    },
                )

                # Verify we got some output
                assert result.content
                result_text = result.content[0].text

                # Check that only the new file is found
                assert "new_file.txt" in result_text
                assert "old_file.txt" not in result_text
        finally:
            # Clean up
            shutil.rmtree(temp_dir)

    async def test_find_by_size(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the find-files tool with size filter."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a small file (less than 10 bytes)
            small_file = os.path.join(temp_dir, "small_file.txt")
            with open(small_file, "w") as f:  # noqa: ASYNC230
                f.write("Small")

            # Create a larger file (more than 10 bytes)
            large_file = os.path.join(temp_dir, "large_file.txt")
            with open(large_file, "w") as f:  # noqa: ASYNC230
                f.write("This is a larger file with more than 10 bytes of content")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                # Call the tool to find files larger than 10 bytes
                result = await session.call_tool(
                    "find-files",
                    {
                        "directory": temp_dir,
                        "arguments": "-size +10c",
                    },
                )

                # Verify we got some output
                assert result.content
                result_text = result.content[0].text

                # Check that only the large file is found
                assert "large_file.txt" in result_text
                assert "small_file.txt" not in result_text
        finally:
            # Clean up
            shutil.rmtree(temp_dir)

    async def test_complex_find_arguments(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-files tool with complex arguments combining multiple conditions."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with complex arguments
            # (Python files not in subfolder1)
            result = await session.call_tool(
                "find-files",
                {
                    "directory": temp_test_directory,
                    "arguments": "-name '*.py' -not -path '*/subfolder1/*'",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that only Python files not in subfolder1 are found
            assert "file2.py" in result_text
            assert "subfolder1/file4.py" not in result_text

    async def test_non_existent_directory(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the find-files tool with a non-existent directory."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with a non-existent directory
            result = await session.call_tool(
                "find-files",
                {"directory": "/path/that/doesnt/exist"},
            )

            # Verify we get some content (likely an error message)
            assert result.content
            result_text = result.content[0].text

            # Just check that we received some output
            assert len(result_text) > 0

    async def test_empty_results(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-files tool with arguments that yield no results."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with arguments that should match no files
            result = await session.call_tool(
                "find-files",
                {
                    "directory": temp_test_directory,
                    "arguments": "-name 'doesnt-exist-*.xyz'",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the result is empty (or contains a message about no results)
            assert result_text.strip() == "" or "No such file or directory" in result_text
