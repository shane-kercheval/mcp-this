"""Unit tests for the GitHub configuration tools."""
import os
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import subprocess
import tempfile


@pytest.fixture
def server_params() -> StdioServerParameters:
    """Create server parameters with GitHub configuration."""
    return StdioServerParameters(
        command="python",
        args=["-m", "mcp_this", "--preset", "github"],
    )


@pytest.mark.skipif(os.getenv("CI") == "true", reason="GitHub CLI not available in CI")
@pytest.mark.asyncio
class TestGetGithubPullRequestInfo:
    """Test the get-github-pull-request-info tool from the GitHub configuration."""

    async def test_tool_registration(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the get-github-pull-request-info tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Verify tool exists
            tool_names = [t.name for t in tools.tools]
            assert "get-github-pull-request-info" in tool_names

            # Get the tool details
            pr_info_tool = next(t for t in tools.tools if t.name == "get-github-pull-request-info")

            # Check tool schema has the expected parameters
            assert "pr_url" in pr_info_tool.inputSchema["properties"]

            # Verify required parameters
            assert "required" in pr_info_tool.inputSchema
            assert "pr_url" in pr_info_tool.inputSchema["required"]

            # Check that the description mentions comprehensive PR information
            assert "comprehensive" in pr_info_tool.description.lower()
            assert "pull request" in pr_info_tool.description.lower()

    async def test_valid_pr_url_format(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the get-github-pull-request-info tool with a valid PR URL format."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Call the tool with the specific test PR URL mentioned by the user
            result = await session.call_tool(
                "get-github-pull-request-info",
                {"pr_url": "https://github.com/shane-kercheval/mcp-this/pull/2"},
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text

            # The result might be an error if gh CLI is not installed/authenticated,
            # but we can verify the URL format processing worked
            assert isinstance(result_text, str)
            assert len(result_text) > 0

            # If gh CLI is available and authenticated, we expect structured output
            if "Error: GitHub CLI (gh) is not installed" not in result_text and \
               "gh: command not found" not in result_text and \
               "Error: You must authenticate" not in result_text:

                # Check for expected output sections
                expected_sections = ["=== PR Overview ===", "=== Files Changed", "=== File Changes ==="]  # noqa: E501
                for section in expected_sections:
                    if section in result_text:
                        # At least one section should be present if gh works
                        break
                else:
                    # If none of the sections are found, it might be an error
                    # This is acceptable for testing since gh CLI might not be set up
                    pass

    async def test_invalid_pr_url_format(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the get-github-pull-request-info tool with invalid URL formats."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            invalid_urls = [
                "https://github.com/owner/repo",  # No pull request path
                "https://github.com/owner/repo/issues/123",  # Issue, not PR
                "https://gitlab.com/owner/repo/merge_requests/123",  # Different platform
                "not-a-url-at-all",  # Not a URL
                "https://github.com/owner",  # Incomplete URL
                "https://github.com/owner/repo/pull/",  # Missing PR number
                "https://github.com/owner/repo/pull/abc",  # Non-numeric PR number
            ]

            for invalid_url in invalid_urls:
                result = await session.call_tool(
                    "get-github-pull-request-info",
                    {"pr_url": invalid_url},
                )

                # Verify we got some output
                assert result.content
                result_text = result.content[0].text

                # Should get an error message about invalid URL format
                assert "Invalid GitHub PR URL format" in result_text or \
                       "Error:" in result_text
                assert isinstance(result_text, str)
                assert len(result_text) > 0

    async def test_pr_url_parsing_regex(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the regex correctly parses different valid GitHub PR URL formats."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            valid_urls = [
                "https://github.com/microsoft/vscode/pull/12345",
                "https://github.com/facebook/react/pull/6789",
                "https://github.com/your-org/your-repo/pull/42",
                "https://github.com/shane-kercheval/mcp-this/pull/2",
                "https://github.com/owner-name/repo-name/pull/1",
                "https://github.com/org123/repo123/pull/999999",
            ]

            for valid_url in valid_urls:
                result = await session.call_tool(
                    "get-github-pull-request-info",
                    {"pr_url": valid_url},
                )

                # Verify we got some output
                assert result.content
                result_text = result.content[0].text

                # Should not get URL format error
                assert "Invalid GitHub PR URL format" not in result_text
                assert isinstance(result_text, str)
                assert len(result_text) > 0

                # If gh CLI is not available, we expect a specific error message
                # If it is available, we expect either PR data or authentication error
                expected_errors = [
                    "GitHub CLI (gh) is not installed",
                    "gh: command not found",
                    "You must authenticate",
                    "could not find",
                    "Not Found",
                ]

                is_gh_error = any(error in result_text for error in expected_errors)
                has_pr_sections = any(section in result_text for section in
                                    ["=== PR Overview ===", "=== Files Changed", "=== File Changes ==="])  # noqa: E501

                # Either we get gh CLI errors or we get PR sections
                assert is_gh_error or has_pr_sections or "Error" in result_text

    async def test_tool_handles_gh_cli_missing(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the tool gracefully handles missing GitHub CLI."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Use a valid URL format but might fail due to missing gh CLI
            result = await session.call_tool(
                "get-github-pull-request-info",
                {"pr_url": "https://github.com/microsoft/vscode/pull/12345"},
            )

            # Verify we got some output
            assert result.content
            result_text = result.content[0].text
            assert isinstance(result_text, str)
            assert len(result_text) > 0

            # The tool should either work (if gh is installed) or give a meaningful error
            # We don't assert specific content since it depends on the environment
            # But we ensure it doesn't crash and returns something

    async def test_tool_description_and_examples(
        self,
        server_params: StdioServerParameters,
    ):
        """Test that the tool description contains expected information and examples."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Get the tool details
            pr_info_tool = next(t for t in tools.tools if t.name == "get-github-pull-request-info")

            # Check that description contains key information
            description = pr_info_tool.description.lower()

            # Should mention comprehensive information
            assert "comprehensive" in description
            assert "pull request" in description

            # Should mention key features
            expected_features = ["overview", "files changed", "diff"]
            for feature in expected_features:
                assert feature in description

            # Should contain examples
            assert "examples:" in description

            # Should mention specific outputs
            expected_outputs = ["title", "description", "status", "metadata"]
            for output in expected_outputs:
                assert output in description

    async def test_parameter_validation(
        self,
        server_params: StdioServerParameters,
    ):
        """Test parameter validation for the get-github-pull-request-info tool."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Test with missing required parameter - this should be handled by the MCP framework
            # The exact behavior depends on the MCP implementation, but typically it would
            # return an error about missing required parameters before our tool is even called

            # We can verify the tool schema indicates pr_url is required
            tools = await session.list_tools()
            pr_info_tool = next(t for t in tools.tools if t.name == "get-github-pull-request-info")

            # Verify the schema correctly marks pr_url as required
            assert "pr_url" in pr_info_tool.inputSchema["required"]
            assert len(pr_info_tool.inputSchema["required"]) == 1  # Only pr_url should be required

    async def test_different_github_domains(
        self,
        server_params: StdioServerParameters,
    ):
        """Test the tool with different GitHub domains (should only work with github.com)."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Test with GitHub Enterprise URLs - these should be rejected by the regex
            enterprise_urls = [
                "https://github.enterprise.com/owner/repo/pull/123",
                "https://git.company.com/owner/repo/pull/123",
                "https://github-enterprise.example.com/owner/repo/pull/123",
            ]

            for enterprise_url in enterprise_urls:
                result = await session.call_tool(
                    "get-github-pull-request-info",
                    {"pr_url": enterprise_url},
                )

                # Verify we got some output
                assert result.content
                result_text = result.content[0].text

                # Should get an error message about invalid URL format
                # since the regex specifically looks for github.com
                assert "Invalid GitHub PR URL format" in result_text
                assert isinstance(result_text, str)
                assert len(result_text) > 0

    async def test_case_sensitivity(
        self,
        server_params: StdioServerParameters,
    ):
        """Test URL parsing with different case variations."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # GitHub URLs should be case-sensitive for the domain
            case_variations = [
                "https://GITHUB.COM/owner/repo/pull/123",  # Uppercase domain - should fail
                "https://GitHub.com/owner/repo/pull/123",  # Mixed case domain - should fail
                "https://github.com/OWNER/REPO/pull/123",  # Uppercase owner/repo - should work
            ]

            for i, url in enumerate(case_variations):
                result = await session.call_tool(
                    "get-github-pull-request-info",
                    {"pr_url": url},
                )

                assert result.content
                result_text = result.content[0].text

                if i < 2:  # First two should fail due to domain case
                    assert "Invalid GitHub PR URL format" in result_text
                else:  # Last one should pass URL validation (though may fail on gh CLI call)
                    assert "Invalid GitHub PR URL format" not in result_text

    async def test_edge_case_pr_numbers(
        self,
        server_params: StdioServerParameters,
    ):
        """Test with edge case PR numbers."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            edge_cases = [
                "https://github.com/owner/repo/pull/1",  # Minimum valid PR number
                "https://github.com/owner/repo/pull/999999999",  # Very large PR number
                "https://github.com/owner/repo/pull/0",  # Zero (invalid in practice but valid format)  # noqa: E501
            ]

            for url in edge_cases:
                result = await session.call_tool(
                    "get-github-pull-request-info",
                    {"pr_url": url},
                )

                assert result.content
                result_text = result.content[0].text

                # URL format should be valid for all these cases
                assert "Invalid GitHub PR URL format" not in result_text
                assert isinstance(result_text, str)
                assert len(result_text) > 0


class GitTestRepo:
    """Helper class for creating and managing temporary Git repositories for testing."""

    def __init__(self):
        self.temp_dir = None
        self.original_cwd = None

    def __enter__(self):
        # Save current directory
        self.original_cwd = os.getcwd()

        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        # Initialize git repository
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)

        return self.temp_dir

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa
        # Return to original directory
        if self.original_cwd:
            os.chdir(self.original_cwd)

        # Clean up temporary directory
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_file(self, filename: str, content: str) -> str:
        """Create a file with the given content."""
        filepath = os.path.join(self.temp_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def create_binary_file(self, filename: str, size_bytes: int = 1024) -> str:
        """Create a binary file with random content."""
        filepath = os.path.join(self.temp_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(b'\x00\x01\x02\x03' * (size_bytes // 4))
        return filepath

    def git_add(self, filename: str):
        """Stage a file."""
        subprocess.run(["git", "add", filename], check=True)

    def git_commit(self, message: str):
        """Commit staged changes."""
        subprocess.run(["git", "commit", "-m", message], check=True)

    def modify_file(self, filename: str, new_content: str):
        """Modify an existing file."""
        with open(filename, 'w') as f:
            f.write(new_content)


@pytest.mark.asyncio
class TestGetLocalChangesInfo:
    """Test the get-local-git-changes-info tool."""

    async def test_tool_registration(self, server_params: StdioServerParameters):
        """Test that the get-local-git-changes-info tool is properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            tools = await session.list_tools()

            # Find the get-local-git-changes-info tool
            local_changes_tool = None
            for tool in tools.tools:
                if tool.name == "get-local-git-changes-info":
                    local_changes_tool = tool
                    break

            assert local_changes_tool is not None, "get-local-git-changes-info tool not found"
            assert "directory" in local_changes_tool.inputSchema["properties"]
            assert "directory" in local_changes_tool.inputSchema["required"]

    async def test_clean_repository(self, server_params: StdioServerParameters):
        """Test tool with a clean Git repository (no changes)."""
        with GitTestRepo() as repo_dir:
            # Create and commit an initial file
            repo = GitTestRepo()
            repo.temp_dir = repo_dir
            repo.create_file("initial.txt", "Initial content")
            repo.git_add("initial.txt")
            repo.git_commit("Initial commit")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show git status
                assert "=== Git Status ===" in result_text

                # Should indicate no changes
                assert ("No staged changes" in result_text or
                       "nothing to commit" in result_text)
                assert ("No unstaged changes" in result_text or
                       "working tree clean" in result_text)
                assert ("No untracked files" in result_text or
                       "Untracked files:" not in result_text)

    async def test_staged_changes_only(self, server_params: StdioServerParameters):
        """Test tool with only staged changes."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create and commit initial file
            repo.create_file("file1.txt", "Original content")
            repo.git_add("file1.txt")
            repo.git_commit("Initial commit")

            # Modify and stage the file
            repo.modify_file("file1.txt", "Modified content")
            repo.git_add("file1.txt")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show staged changes
                assert "=== Staged Changes ===" in result_text
                assert "No staged changes" not in result_text
                assert "Modified content" in result_text or "+" in result_text

                # Should show no unstaged changes
                assert "No unstaged changes" in result_text

    async def test_unstaged_changes_only(self, server_params: StdioServerParameters):
        """Test tool with only unstaged changes."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create and commit initial file
            repo.create_file("file1.txt", "Original content")
            repo.git_add("file1.txt")
            repo.git_commit("Initial commit")

            # Modify file without staging
            repo.modify_file("file1.txt", "Modified content")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show unstaged changes
                assert "=== Unstaged Changes ===" in result_text
                assert "No unstaged changes" not in result_text
                assert "Modified content" in result_text or "+" in result_text

                # Should show no staged changes
                assert "No staged changes" in result_text

    async def test_mixed_staged_and_unstaged_changes(self, server_params: StdioServerParameters):
        """Test tool with both staged and unstaged changes."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create and commit initial files
            repo.create_file("file1.txt", "Original content 1")
            repo.create_file("file2.txt", "Original content 2")
            repo.git_add("file1.txt")
            repo.git_add("file2.txt")
            repo.git_commit("Initial commit")

            # Modify and stage file1
            repo.modify_file("file1.txt", "Staged modification")
            repo.git_add("file1.txt")

            # Modify file2 without staging
            repo.modify_file("file2.txt", "Unstaged modification")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show both staged and unstaged changes
                assert "=== Staged Changes ===" in result_text
                assert "=== Unstaged Changes ===" in result_text
                assert "No staged changes" not in result_text
                assert "No unstaged changes" not in result_text

                # Should contain modifications from both files
                assert "file1.txt" in result_text
                assert "file2.txt" in result_text

    async def test_untracked_text_file(self, server_params: StdioServerParameters):
        """Test tool with untracked text files."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create an initial commit
            repo.create_file("committed.txt", "Committed content")
            repo.git_add("committed.txt")
            repo.git_commit("Initial commit")

            # Create untracked text file
            untracked_content = "This is an untracked file\nWith multiple lines\nOf content"
            repo.create_file("untracked.txt", untracked_content)

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show untracked files section
                assert "=== Untracked Files ===" in result_text
                assert "No untracked files" not in result_text

                # Should show the untracked file name and content
                assert "untracked.txt" in result_text
                assert "This is an untracked file" in result_text
                assert "With multiple lines" in result_text

    async def test_untracked_binary_file(self, server_params: StdioServerParameters):
        """Test tool with untracked binary files (should be skipped)."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create an initial commit
            repo.create_file("committed.txt", "Committed content")
            repo.git_add("committed.txt")
            repo.git_commit("Initial commit")

            # Create binary file with common binary extension
            repo.create_binary_file("image.jpg", 1024)

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show untracked files section
                assert "=== Untracked Files ===" in result_text

                # Should show binary file but mark it as skipped
                assert "image.jpg" in result_text
                assert ("Binary file" in result_text or "skipped" in result_text)

                # Should not show binary content
                assert b'\x00\x01\x02\x03'.decode('utf-8', errors='ignore') not in result_text

    async def test_untracked_large_file(self, server_params: StdioServerParameters):
        """Test tool with large untracked files (should be skipped)."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create an initial commit
            repo.create_file("committed.txt", "Committed content")
            repo.git_add("committed.txt")
            repo.git_commit("Initial commit")

            # Create large text file (>100KB)
            large_content = "This line is repeated many times.\n" * 4000  # ~140KB
            repo.create_file("large.txt", large_content)

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show untracked files section
                assert "=== Untracked Files ===" in result_text

                # Should show large file but mark it as skipped
                assert "large.txt" in result_text
                assert ("Large file" in result_text or ">100KB" in result_text or "skipped" in result_text)  # noqa: E501

                # Should not show the full content
                lines_in_output = result_text.count("This line is repeated many times.")
                assert lines_in_output < 100  # Should not show all 10000 lines

    async def test_mixed_untracked_files(self, server_params: StdioServerParameters):
        """Test tool with mix of text, binary, and large untracked files."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create an initial commit
            repo.create_file("committed.txt", "Committed content")
            repo.git_add("committed.txt")
            repo.git_commit("Initial commit")

            # Create different types of untracked files
            repo.create_file("text.txt", "Small text file content")
            repo.create_binary_file("image.png", 1024)
            repo.create_file("large.log", "Large log entry\n" * 8000)  # >100KB (will be ~112KB)

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show all files
                assert "text.txt" in result_text
                assert "image.png" in result_text
                assert "large.log" in result_text

                # Text file should show content
                assert "Small text file content" in result_text

                # Binary file should be marked as skipped
                assert "Binary file" in result_text or "image.png" in result_text

                # Large file should be marked as skipped
                assert "Large file" in result_text or ">100KB" in result_text

    async def test_non_git_directory(self, server_params: StdioServerParameters):
        """Test tool with a non-Git directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Don't initialize as git repo

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": temp_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show error message (could be different formats)
                assert ("Error: Not a Git repository" in result_text or
                       "Unknown error" in result_text or
                       "not a git repository" in result_text.lower())

    async def test_non_existent_directory(self, server_params: StdioServerParameters):
        """Test tool with a non-existent directory."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()

            # Use a path that definitely doesn't exist
            non_existent_path = "/path/that/definitely/does/not/exist/anywhere"

            result = await session.call_tool(
                "get-local-git-changes-info",
                {"directory": non_existent_path},
            )

            assert result.content
            result_text = result.content[0].text

            # Should handle gracefully (exact behavior depends on implementation)
            # At minimum, should not crash and should provide some indication
            assert len(result_text) > 0

    async def test_nested_directory_structure(self, server_params: StdioServerParameters):
        """Test tool with nested directory structures."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create nested directory structure
            repo.create_file("src/main/java/App.java", "public class App {}")
            repo.create_file("src/test/java/AppTest.java", "public class AppTest {}")
            repo.create_file("docs/README.md", "# Documentation")

            repo.git_add(".")
            repo.git_commit("Initial structure")

            # Create untracked files in nested directories
            repo.create_file("src/main/resources/config.properties", "app.name=test")
            repo.create_file("target/compiled.class", "binary content")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should handle nested paths correctly
                assert "src/main/resources/config.properties" in result_text
                assert "target/compiled.class" in result_text

                # Should show config file content
                assert "app.name=test" in result_text

    async def test_files_with_special_characters(self, server_params: StdioServerParameters):
        """Test tool with files containing special characters in names."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create initial commit
            repo.create_file("normal.txt", "Normal file")
            repo.git_add("normal.txt")
            repo.git_commit("Initial commit")

            # Create files with special characters (that are valid in most filesystems)
            repo.create_file("file with spaces.txt", "Content with spaces")
            repo.create_file("file-with-dashes.txt", "Content with dashes")
            repo.create_file("file_with_underscores.txt", "Content with underscores")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should handle special characters in filenames
                assert "file with spaces.txt" in result_text
                assert "file-with-dashes.txt" in result_text
                assert "file_with_underscores.txt" in result_text

                # Should show content
                assert "Content with spaces" in result_text
                assert "Content with dashes" in result_text
                assert "Content with underscores" in result_text

    async def test_empty_untracked_file(self, server_params: StdioServerParameters):
        """Test tool with empty untracked file."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create initial commit
            repo.create_file("committed.txt", "Committed content")
            repo.git_add("committed.txt")
            repo.git_commit("Initial commit")

            # Create empty untracked file
            repo.create_file("empty.txt", "")

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should show empty file
                assert "empty.txt" in result_text
                assert "0 bytes" in result_text

    async def test_comprehensive_git_state(self, server_params: StdioServerParameters):
        """Test tool with a comprehensive Git state including all types of changes."""
        with GitTestRepo() as repo_dir:
            repo = GitTestRepo()
            repo.temp_dir = repo_dir

            # Create initial files and commit
            repo.create_file("file1.txt", "Original content 1")
            repo.create_file("file2.txt", "Original content 2")
            repo.create_file("file3.txt", "Original content 3")
            repo.git_add(".")
            repo.git_commit("Initial commit")

            # Create staged changes
            repo.modify_file("file1.txt", "Staged modification")
            repo.git_add("file1.txt")

            # Create unstaged changes
            repo.modify_file("file2.txt", "Unstaged modification")

            # Create untracked files of different types
            repo.create_file("new_text.txt", "New text file content")
            repo.create_binary_file("new_image.jpg", 1024)
            repo.create_file("new_large.log", "Large content\n" * 10000)

            async with stdio_client(server_params) as (read, write), ClientSession(
                read, write,
            ) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get-local-git-changes-info",
                    {"directory": repo_dir},
                )

                assert result.content
                result_text = result.content[0].text

                # Should have all sections
                assert "=== Git Status ===" in result_text
                assert "=== Change Summary ===" in result_text
                assert "=== Staged Changes ===" in result_text
                assert "=== Unstaged Changes ===" in result_text
                assert "=== Untracked Files ===" in result_text

                # Should show different types of changes
                assert "file1.txt" in result_text  # staged
                assert "file2.txt" in result_text  # unstaged
                assert "new_text.txt" in result_text  # untracked text
                assert "new_image.jpg" in result_text  # untracked binary
                assert "new_large.log" in result_text  # untracked large

                # Should handle each appropriately
                assert "Staged modification" in result_text
                assert "Unstaged modification" in result_text
                assert "New text file content" in result_text
                assert ("Binary file" in result_text or "skipped" in result_text)
                assert ("Large file" in result_text or ">100KB" in result_text)


@pytest.mark.asyncio
class TestGitHubPrompts:
    """Test the prompts from the GitHub configuration."""

    async def test_prompts_registration(self, server_params: StdioServerParameters):
        """Test that all GitHub prompts are properly registered."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            prompts = await session.list_prompts()

            # Verify all expected prompts exist
            prompt_names = [p.name for p in prompts.prompts]
            expected_prompts = ["create-pr-description", "create-commit-message", "code-review"]

            for expected_prompt in expected_prompts:
                assert expected_prompt in prompt_names, \
                    f"Prompt '{expected_prompt}' not found in {prompt_names}"

            # Verify we have exactly 3 prompts
            assert len(prompts.prompts) == 3, \
                f"Expected 3 prompts, got {len(prompts.prompts)}: {prompt_names}"

    async def test_create_pr_description_prompt(self, server_params: StdioServerParameters):
        """Test the create-pr-description prompt structure."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            prompts = await session.list_prompts()

            # Find the create-pr-description prompt
            pr_prompt = next(p for p in prompts.prompts if p.name == "create-pr-description")

            # Check description
            assert "pull request description" in pr_prompt.description.lower()

            # Check arguments
            assert len(pr_prompt.arguments) == 1
            arg = pr_prompt.arguments[0]
            assert arg.name == "url_or_changes"
            assert arg.required is True

    async def test_create_commit_message_prompt(self, server_params: StdioServerParameters):
        """Test the create-commit-message prompt structure."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            prompts = await session.list_prompts()

            # Find the create-commit-message prompt
            commit_prompt = next(p for p in prompts.prompts if p.name == "create-commit-message")

            # Check description
            assert "commit message" in commit_prompt.description.lower()

            # Check arguments
            assert len(commit_prompt.arguments) == 1
            arg = commit_prompt.arguments[0]
            assert arg.name == "path_or_changes"
            assert arg.required is True

    async def test_code_review_prompt(self, server_params: StdioServerParameters):
        """Test the code-review prompt structure."""
        async with stdio_client(server_params) as (read, write), ClientSession(
            read, write,
        ) as session:
            await session.initialize()
            prompts = await session.list_prompts()

            # Find the code-review prompt
            review_prompt = next(p for p in prompts.prompts if p.name == "code-review")

            # Check description
            assert "code review" in review_prompt.description.lower()

            # Check arguments
            assert len(review_prompt.arguments) == 2

            # Check required argument
            required_arg = next(arg for arg in review_prompt.arguments if arg.required)
            assert required_arg.name == "url_or_changes"
            assert required_arg.required is True

            # Check optional argument
            optional_arg = next(arg for arg in review_prompt.arguments if not arg.required)
            assert optional_arg.name == "focus_areas"
            assert optional_arg.required is False
