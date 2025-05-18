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


@pytest.mark.asyncio
class TestFindTextPatterns:
    """Test the find-text-patterns tool from the default configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the find-text-patterns tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "find-text-patterns" in tool_names

            # Get the tool details
            find_text_patterns_tool = next(
                t for t in tools.tools if t.name == "find-text-patterns"
            )

            # Check tool schema has the expected parameters
            assert "pattern" in find_text_patterns_tool.inputSchema["properties"]
            assert "arguments" in find_text_patterns_tool.inputSchema["properties"]

            # Verify only 'pattern' is required
            assert "required" in find_text_patterns_tool.inputSchema
            assert "pattern" in find_text_patterns_tool.inputSchema["required"]
            assert "arguments" not in find_text_patterns_tool.inputSchema["required"]

    async def test_basic_text_search(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-text-patterns tool with basic text search."""
        # Create test files with specific content
        test_file1 = os.path.join(temp_test_directory, "test_search1.txt")
        test_file2 = os.path.join(temp_test_directory, "test_search2.txt")
        test_file3 = os.path.join(temp_test_directory, "test_search3.py")

        with open(test_file1, "w") as f:  # noqa: ASYNC230
            f.write("This is a test file with the keyword apple.\n"
                    "Another line without the keyword.")

        with open(test_file2, "w") as f:  # noqa: ASYNC230
            f.write("This file has multiple apple mentions.\nHere is another apple on a new line.")

        with open(test_file3, "w") as f:  # noqa: ASYNC230
            f.write("def test_function():\n    # This is a Python file with apple mentioned\n    return 'apple'")  # noqa: E501

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to find the pattern
            result = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "apple",
                    "arguments": temp_test_directory,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that matches are found in all three files
            assert "test_search1.txt" in result_text
            assert "test_search2.txt" in result_text
            assert "test_search3.py" in result_text

            # Check that the correct lines are found
            assert "keyword apple" in result_text
            assert "multiple apple mentions" in result_text
            assert "return 'apple'" in result_text

    async def test_pattern_with_regex(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-text-patterns tool with regex patterns."""
        # Create test files with specific content
        python_file = os.path.join(temp_test_directory, "regex_test.py")
        with open(python_file, "w") as f:  # noqa: ASYNC230
            f.write("""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime

def function1():
    pass

def function2(arg1, arg2=None):
    return arg1 + arg2

class TestClass:
    def method1(self):
        return "test"
""")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to find import statements with regex
            result = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "import.*",
                    "arguments": python_file,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that all import statements are found
            assert "import os" in result_text
            assert "import sys" in result_text
            assert "import numpy" in result_text
            assert "import pandas" in result_text

            # Call the tool to find function definitions with regex
            result2 = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "def function[0-9]",
                    "arguments": python_file,
                },
            )

            # Verify we got some output
            assert result2.content
            result2_text = result2.content[0].text

            # Check that function definitions are found
            assert "def function1" in result2_text
            assert "def function2" in result2_text

    async def test_search_with_context(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-text-patterns tool with context lines."""
        # Create a test file with specific content
        test_file = os.path.join(temp_test_directory, "context_test.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("""Line 1
Line 2
Line 3 with search term
Line 4
Line 5
Line 6 with another search term
Line 7
Line 8
""")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to find pattern with context (1 line before, 2 lines after)
            result = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "search term",
                    "arguments": f"-B 1 -A 2 {test_file}",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that context lines are included
            # For first match
            assert "Line 2" in result_text  # 1 line before
            assert "Line 3 with search term" in result_text  # match
            assert "Line 4" in result_text  # 1 line after
            assert "Line 5" in result_text  # 2 lines after

            # For second match
            assert "Line 5" in result_text  # 1 line before
            assert "Line 6 with another search term" in result_text  # match
            assert "Line 7" in result_text  # 1 line after
            assert "Line 8" in result_text  # 2 lines after

    async def test_search_with_file_filter(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-text-patterns tool with file type filtering."""
        # Create test files with different extensions but same content
        py_file = os.path.join(temp_test_directory, "filter_test.py")
        txt_file = os.path.join(temp_test_directory, "filter_test.txt")
        js_file = os.path.join(temp_test_directory, "filter_test.js")

        file_content = "This file contains the search pattern example"

        for file_path in [py_file, txt_file, js_file]:
            with open(file_path, "w") as f:  # noqa: ASYNC230
                f.write(file_content)

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to search only in Python files
            result = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "search pattern",
                    "arguments": f"{temp_test_directory} --include='*.py'",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that only Python file is included
            assert "filter_test.py" in result_text
            assert "filter_test.txt" not in result_text
            assert "filter_test.js" not in result_text

            # Call the tool to search in both Python and JavaScript files
            result2 = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "search pattern",
                    "arguments": f"{temp_test_directory} --include='*.py' --include='*.js'",
                },
            )

            # Verify we got some output
            assert result2.content
            result2_text = result2.content[0].text

            # Check that both Python and JavaScript files are included
            assert "filter_test.py" in result2_text
            assert "filter_test.js" in result2_text
            assert "filter_test.txt" not in result2_text

    async def test_case_insensitive_search(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-text-patterns tool with case-insensitive search."""
        # Create a test file with mixed case
        test_file = os.path.join(temp_test_directory, "case_test.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("""This has ERROR in uppercase.
This has error in lowercase.
This has Error with mixed case.
""")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with case-sensitive search (default)
            result = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "error",
                    "arguments": test_file,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that only exact case match is found
            assert "lowercase" in result_text
            assert "uppercase" not in result_text
            assert "mixed case" not in result_text

            # Call the tool with case-insensitive search
            result2 = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "error",
                    "arguments": f"-i {test_file}",
                },
            )

            # Verify we got some output
            assert result2.content
            result2_text = result2.content[0].text

            # Check that all variations are found
            assert "lowercase" in result2_text
            assert "uppercase" in result2_text
            assert "mixed case" in result2_text

    async def test_non_existent_pattern(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-text-patterns tool with a pattern that doesn't exist."""
        # Create a test file
        test_file = os.path.join(temp_test_directory, "no_match.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("This file does not contain the search term.")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with a pattern not in the file
            result = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "nonexistentpattern",
                    "arguments": test_file,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # The output might be empty or contain some indication that no matches were found
            # Since implementations may vary, we just check that we got a response but don't
            # validate the specific content
            assert isinstance(result_text, str)

    async def test_search_with_line_numbers(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the find-text-patterns tool showing line numbers."""
        # Create a test file with line numbers
        test_file = os.path.join(temp_test_directory, "line_numbers.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("""Line 1 no match
Line 2 has the pattern
Line 3 no match
Line 4 has the pattern again
Line 5 no match
""")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with line number display
            result = await session.call_tool(
                "find-text-patterns",
                {
                    "pattern": "pattern",
                    "arguments": f"-n {test_file}",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that line numbers are included
            assert ":2:" in result_text
            assert ":4:" in result_text


@pytest.mark.asyncio
class TestExtractFileText:
    """Test the extract-file-text tool from the default configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the extract-file-text tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "extract-file-text" in tool_names

            # Get the tool details
            extract_file_tool = next(t for t in tools.tools if t.name == "extract-file-text")

            # Check tool schema has the expected parameters
            assert "file" in extract_file_tool.inputSchema["properties"]
            assert "arguments" in extract_file_tool.inputSchema["properties"]

            # Verify only 'file' is required
            assert "required" in extract_file_tool.inputSchema
            assert "file" in extract_file_tool.inputSchema["required"]
            assert "arguments" not in extract_file_tool.inputSchema["required"]

    async def test_basic_file_extraction(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the extract-file-text tool with basic usage."""
        # Create a test file
        test_file = os.path.join(temp_test_directory, "extract_test.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("""Line 1: Test content
Line 2: More content
Line 3: Final content""")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to extract the file content
            result = await session.call_tool(
                "extract-file-text",
                {"file": test_file},
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the content is displayed with line numbers
            assert "1" in result_text
            assert "Line 1: Test content" in result_text
            assert "2" in result_text
            assert "Line 2: More content" in result_text
            assert "3" in result_text
            assert "Line 3: Final content" in result_text

    async def test_extract_specific_lines(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the extract-file-text tool with line filtering."""
        # Create a test file with multiple lines
        test_file = os.path.join(temp_test_directory, "multi_line.txt")
        content = "\n".join([f"Line {i}" for i in range(1, 11)])
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write(content)

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to extract specific lines (3-5)
            result = await session.call_tool(
                "extract-file-text",
                {
                    "file": test_file,
                    "arguments": "| sed -n '3,5p'",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that only lines 3-5 are included (with new line numbers starting at 1)
            assert "Line 3" in result_text
            assert "Line 4" in result_text
            assert "Line 5" in result_text
            assert "Line 1" not in result_text
            assert "Line 2" not in result_text
            assert "Line 6" not in result_text

    async def test_extract_with_filtering(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the extract-file-text tool with content filtering."""
        # Create a test file with mixed content
        test_file = os.path.join(temp_test_directory, "mixed_content.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("""INFO: System started
DEBUG: Initializing components
ERROR: Failed to connect to database
INFO: Retrying connection
DEBUG: Connection parameters
ERROR: Connection timeout
INFO: Shutdown initiated""")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to extract only ERROR lines
            result = await session.call_tool(
                "extract-file-text",
                {
                    "file": test_file,
                    "arguments": "| grep ERROR",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that only ERROR lines are included
            assert "ERROR: Failed to connect to database" in result_text
            assert "ERROR: Connection timeout" in result_text
            assert "INFO:" not in result_text
            assert "DEBUG:" not in result_text

    async def test_json_formatting(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the extract-file-text tool with JSON formatting."""
        # Create a test JSON file (unformatted)
        test_file = os.path.join(temp_test_directory, "test.json")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write('{"name":"Test","values":[1,2,3],"nested":{"key":"value"}}')

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to format the JSON
            result = await session.call_tool(
                "extract-file-text",
                {
                    "file": test_file,
                    "arguments": "| python3 -m json.tool",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the JSON is properly formatted
            # Since line numbers might be present and formatting might vary,
            # look for basic patterns
            assert "name" in result_text
            assert "Test" in result_text
            assert "values" in result_text
            assert "nested" in result_text
            assert "key" in result_text
            assert "value" in result_text

            # The formatted output should be longer than the original
            # since it adds spaces and newlines
            assert len(result_text) > len('{"name":"Test","values":[1,2,3],"nested":{"key":"value"}}')  # noqa: E501

    async def test_non_existent_file(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the extract-file-text tool with a non-existent file."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with a non-existent file
            result = await session.call_tool(
                "extract-file-text",
                {"file": "/path/that/doesnt/exist.txt"},
            )

            # Verify we got some output (likely an error message)
            assert result.content
            result_text = result.content[0].text

            # Just check that we received some output
            assert len(result_text) > 0

    async def test_extract_binary_file(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the extract-file-text tool with a binary file."""
        # Create a simple binary file
        binary_file = os.path.join(temp_test_directory, "binary.bin")
        with open(binary_file, "wb") as f:  # noqa: ASYNC230
            f.write(bytes([0x00, 0x01, 0x02, 0x03, 0xFF, 0xFE, 0xFD, 0xFC]))

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to extract the binary content
            result = await session.call_tool(
                "extract-file-text",
                {"file": binary_file},
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Just make sure we got some output, content verification not necessary
            # Binary files may display differently across platforms
            assert isinstance(result_text, str)
            assert len(result_text) > 0


@pytest.mark.asyncio
class TestExtractCodeInfo:
    """Test the extract-code-info tool from the default configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the extract-code-info tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "extract-code-info" in tool_names

            # Get the tool details
            extract_code_tool = next(t for t in tools.tools if t.name == "extract-code-info")

            # Check tool schema has the expected parameters
            assert "files" in extract_code_tool.inputSchema["properties"]
            assert "types" in extract_code_tool.inputSchema["properties"]

            # Verify both parameters are required
            assert "required" in extract_code_tool.inputSchema
            assert "files" in extract_code_tool.inputSchema["required"]
            assert "types" in extract_code_tool.inputSchema["required"]

    async def test_tool_can_be_called(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test that the extract-code-info tool can be called correctly."""
        # Create a simple Python file to analyze
        test_file = os.path.join(temp_test_directory, "test.py")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("print('Hello world')\n")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with minimal arguments
            result = await session.call_tool(
                "extract-code-info",
                {
                    "files": test_file,
                    "types": "functions",
                },
            )

            # Verify that the call returns a result (we don't validate content)
            assert result.content
            result_text = result.content[0].text
            assert isinstance(result_text, str)

    async def test_different_types_parameter(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test that the extract-code-info tool can be called with different types parameters."""
        # Create a simple Python file to analyze
        test_file = os.path.join(temp_test_directory, "multi_type.py")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("print('Hello world')\n")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with different types parameter
            result = await session.call_tool(
                "extract-code-info",
                {
                    "files": test_file,
                    "types": "classes",
                },
            )

            # Verify that the call returns a result (we don't validate content)
            assert result.content
            result_text = result.content[0].text
            assert isinstance(result_text, str)



    async def test_multiple_types_parameter(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test that the extract-code-info tool can be called with multiple types parameters."""
        # Create a simple Python file to analyze
        test_file = os.path.join(temp_test_directory, "multi_param.py")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("print('Hello world')\n")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with multiple types parameter
            result = await session.call_tool(
                "extract-code-info",
                {
                    "files": test_file,
                    "types": "functions,classes,imports,todos",
                },
            )

            # Verify that the call returns a result (we don't validate content)
            assert result.content
            result_text = result.content[0].text
            assert isinstance(result_text, str)



    async def test_non_existent_file(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the extract-code-info tool with a non-existent file."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with a non-existent file
            result = await session.call_tool(
                "extract-code-info",
                {
                    "files": "/path/that/doesnt/exist.py",
                    "types": "functions",
                },
            )

            # Verify we got some output (likely an error message or empty result)
            assert result.content
            result_text = result.content[0].text

            # Just check that we received some output
            assert isinstance(result_text, str)
            assert len(result_text) > 0


@pytest.mark.asyncio
class TestEditFile:
    """Test the edit-file tool from the default configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the edit-file tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "edit-file" in tool_names

            # Get the tool details
            edit_file_tool = next(t for t in tools.tools if t.name == "edit-file")

            # Check tool schema has the expected parameters
            expected_parameters = [
                "file", "operation", "anchor", "content", "start_line", "end_line",
            ]
            for param in expected_parameters:
                assert param in edit_file_tool.inputSchema["properties"]

            # Verify required parameters
            assert "required" in edit_file_tool.inputSchema
            assert "file" in edit_file_tool.inputSchema["required"]
            assert "operation" in edit_file_tool.inputSchema["required"]

    async def test_basic_operation(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test that the edit-file tool can be called successfully."""
        # Create a test file
        test_file = os.path.join(temp_test_directory, "test_edit.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("Line 1\nLine 2\nLine 3\n")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with a basic operation
            result = await session.call_tool(
                "edit-file",
                {
                    "file": test_file,
                    "operation": "replace",
                    "anchor": "Line 2",
                    "content": "Replaced Line",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # We just verify that the command returned some output
            assert isinstance(result_text, str)
            assert len(result_text) > 0

    async def test_with_different_operations(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the edit-file tool with different operations."""
        # Create a test file
        test_file = os.path.join(temp_test_directory, "test_operations.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("Line 1\nLine 2\nLine 3\n")

        operations = [
            "insert_after",
            "insert_before",
            "replace",
            "delete",
        ]

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with each operation
            for operation in operations:
                params = {
                    "file": test_file,
                    "operation": operation,
                    "anchor": "Line 2",
                }

                # Content is required for all operations except delete
                if operation != "delete":
                    params["content"] = "Test Content"

                # Call the tool
                result = await session.call_tool("edit-file", params)

                # Verify we got some output
                assert result.content
                result_text = result.content[0].text

                # We just verify that the command returned some output
                assert isinstance(result_text, str)
                assert len(result_text) > 0

    async def test_replace_range_operation(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the edit-file tool with replace_range operation."""
        # Create a test file
        test_file = os.path.join(temp_test_directory, "test_replace_range.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to replace a range of lines
            result = await session.call_tool(
                "edit-file",
                {
                    "file": test_file,
                    "operation": "replace_range",
                    "start_line": "2",
                    "end_line": "4",
                    "content": "Replaced Range",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # We just verify that the command returned some output
            assert isinstance(result_text, str)
            assert len(result_text) > 0



    async def test_with_invalid_operation(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the edit-file tool with an invalid operation."""
        # Create a test file
        test_file = os.path.join(temp_test_directory, "test_invalid.txt")
        with open(test_file, "w") as f:  # noqa: ASYNC230
            f.write("Line 1\nLine 2\nLine 3\n")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with an invalid operation
            result = await session.call_tool(
                "edit-file",
                {
                    "file": test_file,
                    "operation": "invalid_operation",
                    "anchor": "Line 2",
                    "content": "New Content",
                },
            )

            # Verify we got some output (likely an error message)
            assert result.content
            result_text = result.content[0].text

            # We just verify that the command returned some output
            assert isinstance(result_text, str)
            assert len(result_text) > 0

    async def test_non_existent_file(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test the edit-file tool with a non-existent file."""
        non_existent_file = os.path.join(temp_test_directory, "non_existent.txt")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with a non-existent file
            result = await session.call_tool(
                "edit-file",
                {
                    "file": non_existent_file,
                    "operation": "insert_after",
                    "anchor": "Pattern",
                    "content": "New Content",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # The exact error message might vary by implementation
            # Just check that we got some output
            assert isinstance(result_text, str)
            assert len(result_text) > 0


@pytest.mark.asyncio
class TestCreateFile:
    """Test the create-file tool from the default configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the create-file tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "create-file" in tool_names

            # Get the tool details
            create_file_tool = next(t for t in tools.tools if t.name == "create-file")

            # Check tool schema has the expected parameters
            assert "path" in create_file_tool.inputSchema["properties"]
            assert "content" in create_file_tool.inputSchema["properties"]

            # Verify required parameters
            assert "required" in create_file_tool.inputSchema
            assert "path" in create_file_tool.inputSchema["required"]
            assert "content" in create_file_tool.inputSchema["required"]

    async def test_create_simple_file(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test creating a simple file."""
        # Define a file path
        test_file = os.path.join(temp_test_directory, "test_create.txt")
        file_content = "This is a test file content"

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to create a file
            result = await session.call_tool(
                "create-file",
                {
                    "path": test_file,
                    "content": file_content,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the call was successful
            assert "File created successfully" in result_text or "created successfully" in result_text  # noqa: E501

            # Verify the file exists
            assert os.path.exists(test_file)
            # Read file and strip any trailing whitespace/newlines for comparison
            with open(test_file) as f:  # noqa: ASYNC230
                content = f.read().strip()
                assert content == file_content.strip()

    async def test_create_file_with_nested_directory(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test creating a file in a nested directory that doesn't exist yet."""
        # Define a file path in a nested directory that doesn't exist
        nested_dir = os.path.join(temp_test_directory, "nested", "subdirectory")
        test_file = os.path.join(nested_dir, "test_nested.txt")
        file_content = "This file is in a nested directory"

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to create a file (should create parent directories)
            result = await session.call_tool(
                "create-file",
                {
                    "path": test_file,
                    "content": file_content,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the call was successful
            assert "File created successfully" in result_text or "created successfully" in result_text  # noqa: E501

            # Verify the directory and file exist
            assert os.path.exists(nested_dir)
            assert os.path.exists(test_file)
            # Read file and strip any trailing whitespace/newlines for comparison
            with open(test_file) as f:  # noqa: ASYNC230
                content = f.read().strip()
                assert content == file_content.strip()

    async def test_create_file_that_already_exists(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test creating a file that already exists."""
        # Create a file first
        existing_file = os.path.join(temp_test_directory, "existing.txt")
        with open(existing_file, "w") as f:  # noqa: ASYNC230
            f.write("Original content")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to try to create the same file
            result = await session.call_tool(
                "create-file",
                {
                    "path": existing_file,
                    "content": "New content",
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the operation didn't succeed
            # The exact message might vary but it should indicate the file already exists
            assert "already exists" in result_text or "Error" in result_text

            # Verify the file still has the original content
            with open(existing_file) as f:  # noqa: ASYNC230
                content = f.read()
                assert content == "Original content"


@pytest.mark.asyncio
class TestCreateDirectory:
    """Test the create-directory tool from the default configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the create-directory tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "create-directory" in tool_names

            # Get the tool details
            create_dir_tool = next(t for t in tools.tools if t.name == "create-directory")

            # Check tool schema has the expected parameters
            assert "path" in create_dir_tool.inputSchema["properties"]

            # Verify required parameters
            assert "required" in create_dir_tool.inputSchema
            assert "path" in create_dir_tool.inputSchema["required"]

    async def test_create_simple_directory(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test creating a simple directory."""
        # Define a directory path
        test_dir = os.path.join(temp_test_directory, "test_create_dir")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to create a directory
            result = await session.call_tool(
                "create-directory",
                {
                    "path": test_dir,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the call was successful
            assert "Directory created successfully" in result_text or "created successfully" in result_text  # noqa: E501

            # Verify the directory exists
            assert os.path.exists(test_dir)
            assert os.path.isdir(test_dir)

    async def test_create_nested_directory(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test creating a nested directory structure."""
        # Define a nested directory path
        nested_dir = os.path.join(temp_test_directory, "nested", "multi", "level", "directory")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to create a nested directory structure
            result = await session.call_tool(
                "create-directory",
                {
                    "path": nested_dir,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check that the call was successful
            assert "Directory created successfully" in result_text or "created successfully" in result_text  # noqa: E501

            # Verify the directory exists
            assert os.path.exists(nested_dir)
            assert os.path.isdir(nested_dir)

            # Verify parent directories were also created
            parent_dir = os.path.join(temp_test_directory, "nested", "multi", "level")
            assert os.path.exists(parent_dir)
            assert os.path.isdir(parent_dir)

    async def test_create_directory_that_already_exists(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test creating a directory that already exists."""
        # Create a directory first
        existing_dir = os.path.join(temp_test_directory, "existing_dir")
        os.makedirs(existing_dir)

        # Create a file in the directory to verify it's not affected
        marker_file = os.path.join(existing_dir, "marker.txt")
        with open(marker_file, "w") as f:  # noqa: ASYNC230
            f.write("This is a marker file")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool to create the same directory
            result = await session.call_tool(
                "create-directory",
                {
                    "path": existing_dir,
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # The operation should succeed (mkdir -p is idempotent)
            assert "Directory created successfully" in result_text or "created successfully" in result_text  # noqa: E501

            # The marker file should still exist
            assert os.path.exists(marker_file)


@pytest.mark.asyncio
class TestWebScraper:
    """Test the web-scraper tool from the default configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the web-scraper tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "web-scraper" in tool_names

            # Get the tool details
            web_scraper_tool = next(t for t in tools.tools if t.name == "web-scraper")

            # Check tool schema has the expected parameters
            assert "url" in web_scraper_tool.inputSchema["properties"]
            assert "dump_options" in web_scraper_tool.inputSchema["properties"]

            # Verify required parameters
            assert "required" in web_scraper_tool.inputSchema
            assert "url" in web_scraper_tool.inputSchema["required"]
            assert "dump_options" not in web_scraper_tool.inputSchema["required"]

    async def test_basic_scraping(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the web-scraper tool with basic usage - using a simple, stable URL."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with a stable URL (example.com)
            result = await session.call_tool(
                "web-scraper",
                {"url": "http://example.com"},
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # Check for expected content in the output
            # example.com is very stable and should contain these phrases
            assert "Example Domain" in result_text
            assert "illustrative examples" in result_text

    async def test_with_dump_options(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the web-scraper tool with custom dump options."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with custom width option
            result = await session.call_tool(
                "web-scraper",
                {
                    "url": "http://example.com",
                    "dump_options": "-width=50",  # Set a narrow width
                },
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # The content should still contain the expected text
            assert "Example Domain" in result_text

            # Test with source option to get HTML
            result2 = await session.call_tool(
                "web-scraper",
                {
                    "url": "http://example.com",
                    "dump_options": "-source",  # Get source HTML
                },
            )

            # Verify we got some output
            assert result2.content
            result2_text = result2.content[0].text

            # Source HTML should contain HTML tags
            assert "<html" in result2_text
            assert "<head" in result2_text
            assert "<body" in result2_text

    async def test_invalid_url(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the web-scraper tool with an invalid or non-existent URL."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with an invalid URL
            result = await session.call_tool(
                "web-scraper",
                {"url": "http://this-domain-does-not-exist-123456789.com"},
            )

            # Verify we got some output (likely an error message)
            assert result.content
            result_text = result.content[0].text

            # Just check that we received some output
            assert len(result_text) > 0
