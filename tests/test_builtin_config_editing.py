"""Unit tests for the editing tools."""
import pytest
import aiofiles
import tempfile
import os
import shutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture
def server_params() -> StdioServerParameters:
    """Create server parameters with default configuration."""
    return StdioServerParameters(
        command="python",
        args=["-m", "mcp_this", "--preset", "editing"],
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
class TestEditFile:
    """Test the edit-file tool from the editing configuration."""

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
            assert 'Error' not in result_text

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
                assert 'Error' not in result_text

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
            assert 'Error' not in result_text

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
            assert 'Error' in result_text
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
            assert 'Error' in result_text
            assert isinstance(result_text, str)
            assert len(result_text) > 0


@pytest.mark.asyncio
class TestCreateFile:
    """Test the create-file tool from the editing configuration."""

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
            assert "content" not in create_file_tool.inputSchema["required"]

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
            assert 'Error' not in result_text

            # Check that the call was successful
            assert "File created successfully" in result_text or "created successfully" in result_text  # noqa: E501

            # Verify the file exists
            assert os.path.exists(test_file)
            # Read file and strip any trailing whitespace/newlines for comparison
            async with aiofiles.open(test_file) as f:
                content = await f.read()
                assert content == file_content

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
            assert 'Error' not in result_text

            # Check that the call was successful
            assert "File created successfully" in result_text or "created successfully" in result_text  # noqa: E501

            # Verify the directory and file exist
            assert os.path.exists(nested_dir)
            assert os.path.exists(test_file)
            # Read file and strip any trailing whitespace/newlines for comparison
            async with aiofiles.open(test_file) as f:
                content = await f.read()
                assert content == file_content

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

    async def test_create_file_with_multiline_content(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test creating a file with multiline content preserves newlines."""
        test_file = os.path.join(temp_test_directory, "multiline.txt")
        file_content = "Line 1\nLine 2\nLine 3\n"  # Note the newlines

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            result = await session.call_tool(
                "create-file",
                {
                    "path": test_file,
                    "content": file_content,
                },
            )

            assert result.content
            result_text = result.content[0].text
            assert 'Error' not in result_text
            assert "File created successfully" in result_text

            # Verify exact content match (no stripping!)
            async with aiofiles.open(test_file) as f:
                actual_content = await f.read()
                assert actual_content == file_content  # Exact match including newlines

            # Also verify line count
            async with aiofiles.open(test_file) as f:
                lines = await f.readlines()
                assert len(lines) == 3  # Should be 3 separate lines
                assert lines[0] == "Line 1\n"
                assert lines[1] == "Line 2\n"
                assert lines[2] == "Line 3\n"

    async def test_create_empty_file(
        self,
        server_params: StdioServerParameters,
        temp_test_directory: str,
    ):
        """Test creating an empty file."""
        test_file = os.path.join(temp_test_directory, "empty.txt")

        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            result = await session.call_tool(
                "create-file",
                {
                    "path": test_file,
                    # No content parameter
                },
            )

            assert result.content
            result_text = result.content[0].text
            assert 'Error' not in result_text

            # Verify file exists and is empty
            assert os.path.exists(test_file)
            async with aiofiles.open(test_file) as f:
                content = await f.read()
                assert content == ""


@pytest.mark.asyncio
class TestCreateDirectory:
    """Test the create-directory tool from the editing configuration."""

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
            assert 'Error' not in result_text

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
            assert 'Error' not in result_text

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
            assert 'Error' not in result_text

            # The operation should succeed (mkdir -p is idempotent)
            assert "Directory created successfully" in result_text or "created successfully" in result_text  # noqa: E501

            # The marker file should still exist
            assert os.path.exists(marker_file)

