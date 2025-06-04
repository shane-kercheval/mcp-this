"""Unit tests for the prompts module."""
import pytest
from mcp_this.prompts import (
    PromptInfo,
    PromptArgument,
    parse_prompts,
    validate_prompt_config,
)


class TestParsePrompts:
    """Test cases for the parse_prompts function."""

    def test_no_prompts(self):
        """Test parsing a configuration with no prompts section."""
        config = {"tools": {}}
        result = parse_prompts(config)
        assert result == []

    def test_empty_prompts(self):
        """Test parsing a configuration with an empty prompts section."""
        config = {"prompts": {}}
        result = parse_prompts(config)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_basic_prompt(self):
        """Test parsing a basic prompt with no arguments."""
        config = {
            "prompts": {
                "simple-prompt": {
                    "description": "A simple prompt",
                    "template": "This is a simple prompt template",
                },
            },
        }
        result = parse_prompts(config)
        assert len(result) == 1

        prompt = result[0]
        assert isinstance(prompt, PromptInfo)
        assert prompt.name == "simple-prompt"
        assert prompt.description == "A simple prompt"
        assert prompt.template == "This is a simple prompt template"
        assert prompt.arguments == {}

    def test_prompt_with_arguments(self):
        """Test parsing a prompt with arguments."""
        config = {
            "prompts": {
                "code-review": {
                    "description": "Review code for best practices",
                    "template": "Please review this code: {{code}}",
                    "arguments": {
                        "code": {
                            "description": "Code to review",
                            "required": True,
                        },
                        "focus": {
                            "description": "Focus areas",
                            "required": False,
                        },
                    },
                },
            },
        }
        result = parse_prompts(config)
        assert len(result) == 1

        prompt = result[0]
        assert prompt.name == "code-review"
        assert prompt.description == "Review code for best practices"
        assert len(prompt.arguments) == 2

        code_arg = prompt.arguments["code"]
        assert isinstance(code_arg, PromptArgument)
        assert code_arg.description == "Code to review"
        assert code_arg.required is True

        focus_arg = prompt.arguments["focus"]
        assert isinstance(focus_arg, PromptArgument)
        assert focus_arg.description == "Focus areas"
        assert focus_arg.required is False

    def test_multiple_prompts(self):
        """Test parsing multiple prompts."""
        config = {
            "prompts": {
                "pr-description": {
                    "description": "Generate PR description",
                    "template": "Generate a PR description for: {{changes}}",
                    "arguments": {
                        "changes": {
                            "description": "Summary of changes",
                            "required": True,
                        },
                    },
                },
                "code-review": {
                    "description": "Review code",
                    "template": "Review this code: {{code}}",
                    "arguments": {
                        "code": {
                            "description": "Code to review",
                            "required": True,
                        },
                    },
                },
            },
        }
        result = parse_prompts(config)
        assert len(result) == 2

        prompt_names = [p.name for p in result]
        assert "pr-description" in prompt_names
        assert "code-review" in prompt_names

    def test_invalid_prompts_config(self):
        """Test that invalid prompts configuration raises ValueError."""
        # Invalid prompts type
        config = {"prompts": "not a dict"}
        with pytest.raises(ValueError, match="'prompts' must be a dictionary"):
            parse_prompts(config)


class TestValidatePromptConfig:
    """Test cases for the validate_prompt_config function."""

    def test_valid_prompt_config(self):
        """Test validating a valid prompt configuration."""
        config = {
            "description": "A test prompt",
            "template": "Test template",
            "arguments": {
                "arg1": {
                    "description": "First argument",
                    "required": True,
                },
            },
        }
        # Should not raise an exception
        validate_prompt_config("test-prompt", config)

    def test_prompt_config_not_dict(self):
        """Test validation fails when prompt config is not a dict."""
        with pytest.raises(ValueError, match="Prompt 'test' must be a dictionary"):
            validate_prompt_config("test", "not a dict")

    def test_missing_description(self):
        """Test validation fails when description is missing."""
        config = {"arguments": {}}
        with pytest.raises(ValueError, match="Prompt 'test' must contain a 'description'"):
            validate_prompt_config("test", config)

    def test_description_not_string(self):
        """Test validation fails when description is not a string."""
        config = {"description": 123}
        with pytest.raises(ValueError, match="Prompt 'test' description must be a string"):
            validate_prompt_config("test", config)

    def test_missing_template(self):
        """Test validation fails when template is missing."""
        config = {"description": "Test prompt"}
        with pytest.raises(ValueError, match="Prompt 'test' must contain a 'template'"):
            validate_prompt_config("test", config)

    def test_template_not_string(self):
        """Test validation fails when template is not a string."""
        config = {"description": "Test prompt", "template": 123}
        with pytest.raises(ValueError, match="Prompt 'test' template must be a string"):
            validate_prompt_config("test", config)

    def test_arguments_not_dict(self):
        """Test validation fails when arguments is not a dict."""
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": "not a dict",
        }
        with pytest.raises(ValueError, match="Prompt 'test' arguments must be a dictionary"):
            validate_prompt_config("test", config)

    def test_argument_config_not_dict(self):
        """Test validation fails when an argument config is not a dict."""
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": {
                "arg1": "not a dict",
            },
        }
        with pytest.raises(
            ValueError, match="Argument 'arg1' in prompt 'test' must be a dictionary",
        ):
            validate_prompt_config("test", config)

    def test_argument_missing_description(self):
        """Test validation fails when argument description is missing."""
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": {
                "arg1": {
                    "required": True,
                },
            },
        }
        with pytest.raises(
            ValueError, match="Argument 'arg1' in prompt 'test' must contain a 'description'",
        ):
            validate_prompt_config("test", config)

    def test_argument_missing_required(self):
        """Test validation fails when argument required field is missing."""
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": {
                "arg1": {
                    "description": "Test arg",
                },
            },
        }
        with pytest.raises(
            ValueError, match="Argument 'arg1' in prompt 'test' must contain a 'required' field",
        ):
            validate_prompt_config("test", config)

    def test_argument_required_not_bool(self):
        """Test validation fails when argument required field is not a boolean."""
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": {
                "arg1": {
                    "description": "Test arg",
                    "required": "yes",
                },
            },
        }
        with pytest.raises(
            ValueError, match="Argument 'arg1' required field in prompt 'test' must be a boolean",
        ):
            validate_prompt_config("test", config)

    def test_invalid_argument_names_rejected(self):
        """Test validation fails when argument names contain invalid characters."""
        # Test argument name with spaces
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": {
                "invalid arg": {  # Spaces not allowed
                    "description": "Invalid argument with spaces",
                    "required": True,
                },
            },
        }
        with pytest.raises(ValueError, match="contains invalid characters"):
            validate_prompt_config("test", config)

        # Test argument name starting with number
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": {
                "123invalid": {  # Cannot start with number
                    "description": "Invalid argument starting with number",
                    "required": False,
                },
            },
        }
        with pytest.raises(ValueError, match="contains invalid characters"):
            validate_prompt_config("test", config)

        # Test argument name with dashes
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": {
                "invalid-dash": {  # Dashes not allowed
                    "description": "Invalid argument with dash",
                    "required": False,
                },
            },
        }
        with pytest.raises(ValueError, match="contains invalid characters"):
            validate_prompt_config("test", config)

    def test_valid_argument_names_accepted(self):
        """Test validation passes for valid argument names."""
        config = {
            "description": "Test prompt",
            "template": "Test template",
            "arguments": {
                "valid_arg": {
                    "description": "Valid argument",
                    "required": True,
                },
                "_another_valid_arg": {
                    "description": "Another valid argument starting with underscore",
                    "required": False,
                },
                "arg123": {
                    "description": "Valid argument with numbers",
                    "required": False,
                },
            },
        }
        # Should not raise any exception
        validate_prompt_config("test", config)
