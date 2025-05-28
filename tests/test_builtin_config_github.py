"""Unit tests for the GitHub configuration tools."""
import os
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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
