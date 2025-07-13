"""Unit tests for template rendering functionality in prompts."""
from mcp_this.prompts import parse_prompts
from mcp_this.mcp_server import render_template


class TestTemplateRendering:
    """Test cases for template rendering functionality."""

    def test_basic_variable_substitution(self):
        """Test basic variable substitution with {{variable}}."""
        result = render_template("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_template_with_no_variables(self):
        """Test template rendering with no variables."""
        result = render_template("Hello, World!", {})
        assert result == "Hello, World!"

    def test_multiple_variable_substitution(self):
        """Test substitution of multiple variables."""
        template = "Hello {{name}}, welcome to {{place}}!"
        result = render_template(template, {"name": "Alice", "place": "Python"})
        assert result == "Hello Alice, welcome to Python!"

    def test_empty_variable_not_substituted(self):
        """Test that empty variables are not substituted."""
        template = "Hello {{name}}{{suffix}}"
        result = render_template(template, {"name": "World", "suffix": ""})
        assert result == "Hello World"

    def test_none_variable_not_substituted(self):
        """Test that None variables are not substituted."""
        template = "Hello {{name}}{{suffix}}"
        result = render_template(template, {"name": "World", "suffix": None})
        assert result == "Hello World"

    def test_missing_variable_removed(self):
        """Test that missing variables are cleaned up."""
        template = "Hello {{name}} {{missing_var}}"
        result = render_template(template, {"name": "World"})
        assert result == "Hello World"

    def test_if_block_with_truthy_variable(self):
        """Test {{#if}} block when variable is truthy."""
        template = "Hello{{#if name}} {{name}}{{/if}}!"
        result = render_template(template, {"name": "World"})
        assert result == "Hello World!"

    def test_if_block_with_falsy_variable(self):
        """Test {{#if}} block when variable is falsy."""
        template = "Hello{{#if name}} {{name}}{{/if}}!"
        result = render_template(template, {"name": ""})
        assert result == "Hello!"

    def test_if_block_with_missing_variable(self):
        """Test {{#if}} block when variable is missing."""
        template = "Hello{{#if name}} {{name}}{{/if}}!"
        result = render_template(template, {})
        assert result == "Hello!"

    def test_if_block_multiline(self):
        """Test {{#if}} block with multiline content."""
        template = """Hello{{#if details}}
Additional details:
{{details}}{{/if}}
Done."""
        result = render_template(template, {"details": "Some info"})
        expected = """Hello
Additional details:
Some info
Done."""
        assert result == expected

    def test_if_block_multiline_false(self):
        """Test {{#if}} block with multiline content when condition is false."""
        template = """Hello{{#if details}}
Additional details:
{{details}}{{/if}}
Done."""
        result = render_template(template, {})
        expected = """Hello
Done."""
        assert result == expected

    def test_if_else_block_true_condition(self):
        """Test {{#if}}...{{else}}...{{/if}} when condition is true."""
        template = "{{#if name}}Hello {{name}}{{else}}Hello stranger{{/if}}!"
        result = render_template(template, {"name": "Alice"})
        assert result == "Hello Alice!"

    def test_if_else_block_false_condition(self):
        """Test {{#if}}...{{else}}...{{/if}} when condition is false."""
        template = "{{#if name}}Hello {{name}}{{else}}Hello stranger{{/if}}!"
        result = render_template(template, {"name": ""})
        assert result == "Hello stranger!"

    def test_if_else_block_missing_variable(self):
        """Test {{#if}}...{{else}}...{{/if}} when variable is missing."""
        template = "{{#if name}}Hello {{name}}{{else}}Hello stranger{{/if}}!"
        result = render_template(template, {})
        assert result == "Hello stranger!"

    def test_if_else_block_multiline(self):
        """Test {{#if}}...{{else}}...{{/if}} with multiline content."""
        template = """Welcome!
{{#if user}}
You are logged in as {{user}}.
Access granted.
{{else}}
Please log in to continue.
Access denied.
{{/if}}
Thank you."""
        # Test with user
        result = render_template(template, {"user": "admin"})
        expected = """Welcome!

You are logged in as admin.
Access granted.

Thank you."""
        assert result == expected

        # Test without user
        result = render_template(template, {})
        expected = """Welcome!

Please log in to continue.
Access denied.

Thank you."""
        assert result == expected

    def test_single_line_if_statement(self):
        """Test single line {{#if}} statement."""
        template = "File: {{filename}}{{#if size}} ({{size}} bytes){{/if}}"
        # With size
        result = render_template(template, {"filename": "test.txt", "size": "1024"})
        assert result == "File: test.txt (1024 bytes)"

        # Without size
        result = render_template(template, {"filename": "test.txt"})
        assert result == "File: test.txt"

    def test_single_line_if_else_statement(self):
        """Test single line {{#if}}...{{else}}...{{/if}} statement."""
        template = "Status: {{#if active}}Online{{else}}Offline{{/if}}"

        # Active
        result = render_template(template, {"active": "true"})
        assert result == "Status: Online"

        # Inactive
        result = render_template(template, {"active": ""})
        assert result == "Status: Offline"

    def test_nested_variable_in_if_block(self):
        """Test variables inside {{#if}} blocks."""
        template = "{{#if greeting}}{{greeting}} {{name}}{{else}}Hello {{name}}{{/if}}!"

        # With custom greeting
        result = render_template(template, {"greeting": "Hi", "name": "Bob"})
        assert result == "Hi Bob!"

        # Without custom greeting
        result = render_template(template, {"name": "Bob"})
        assert result == "Hello Bob!"

    def test_multiple_if_blocks(self):
        """Test multiple {{#if}} blocks in same template."""
        template = """Name: {{name}}
{{#if email}}Email: {{email}}{{/if}}
{{#if phone}}Phone: {{phone}}{{else}}No phone provided{{/if}}
{{#if address}}Address: {{address}}{{/if}}"""
        result = render_template(template, {
            "name": "John",
            "email": "john@example.com",
            "phone": "",
            "address": "123 Main St",
        })

        expected = """Name: John
Email: john@example.com
No phone provided
Address: 123 Main St"""
        assert result == expected

    def test_complex_template(self):
        """Test a complex template with multiple features."""
        template = """{{#if prompt_name}}{{prompt_name}}{{else}}task-prompt{{/if}}

Subject: {{subject}}
{{#if priority}}Priority: {{priority}}{{/if}}
{{#if details}}
Details:
{{details}}
{{else}}
No additional details provided.
{{/if}}

{{#if urgent}}⚠️  URGENT: This requires immediate attention!{{/if}}
Status: {{#if completed}}✅ Complete{{else}}⏳ Pending{{/if}}"""

        # Test with all fields
        result = render_template(template, {
            "prompt_name": "custom-task",
            "subject": "Fix bug",
            "priority": "High",
            "details": "Critical security issue",
            "urgent": "true",
            "completed": "",
        })

        expected = """custom-task

Subject: Fix bug
Priority: High

Details:
Critical security issue


⚠️  URGENT: This requires immediate attention!
Status: ⏳ Pending"""
        assert result == expected

        # Test with minimal fields
        result = render_template(template, {
            "subject": "Review code",
            "completed": "true",
        })

        expected = """task-prompt

Subject: Review code


No additional details provided.



Status: ✅ Complete"""
        assert result == expected

    def test_numeric_variables(self):
        """Test that numeric variables are properly converted to strings."""
        template = "Count: {{count}}{{#if total}} of {{total}}{{/if}}"
        result = render_template(template, {"count": 5, "total": 10})
        assert result == "Count: 5 of 10"

    def test_boolean_variables_as_strings(self):
        """Test that boolean variables work when provided as strings."""
        template = "{{#if enabled}}Feature enabled{{else}}Feature disabled{{/if}}"

        # String representations of booleans
        result = render_template(template, {"enabled": "true"})
        assert result == "Feature enabled"

        result = render_template(template, {"enabled": "false"})
        assert result == "Feature enabled"  # Non-empty string is truthy

        result = render_template(template, {"enabled": ""})
        assert result == "Feature disabled"  # Empty string is falsy

    def test_whitespace_handling(self):
        """Test that whitespace in templates is preserved correctly."""
        template = "  {{#if indent}}    Indented content{{/if}}  "
        result = render_template(template, {"indent": "yes"})
        assert result == "Indented content"  # strip() removes leading/trailing whitespace

    def test_special_characters_in_variables(self):
        """Test that special characters in variables are preserved."""
        template = "Message: {{message}}"
        result = render_template(template, {"message": "Hello & welcome! <test>"})
        assert result == "Message: Hello & welcome! <test>"


class TestPromptIntegration:
    """Integration tests for prompt parsing and template rendering."""

    def test_parse_prompts_with_if_blocks(self):
        """Test parsing prompts that contain {{#if}} blocks."""
        config = {
            "prompts": {
                "test-prompt": {
                    "description": "A test prompt with conditionals",
                    "template": "Hello {{name}}{{#if title}}, {{title}}{{/if}}!",
                    "arguments": {
                        "name": {
                            "description": "Person's name",
                            "required": True,
                        },
                        "title": {
                            "description": "Person's title",
                            "required": False,
                        },
                    },
                },
            },
        }

        prompts = parse_prompts(config)
        assert len(prompts) == 1

        prompt = prompts[0]
        assert prompt.name == "test-prompt"
        assert "{{#if title}}" in prompt.template
        assert len(prompt.arguments) == 2

    def test_parse_prompts_with_if_else_blocks(self):
        """Test parsing prompts that contain {{#if}}...{{else}}...{{/if}} blocks."""
        config = {
            "prompts": {
                "greeting-prompt": {
                    "description": "A conditional greeting prompt",
                    "template": "{{#if formal}}Good day, {{name}}.{{else}}Hey {{name}}!{{/if}}",
                    "arguments": {
                        "name": {
                            "description": "Person's name",
                            "required": True,
                        },
                        "formal": {
                            "description": "Use formal greeting",
                            "required": False,
                        },
                    },
                },
            },
        }

        prompts = parse_prompts(config)
        assert len(prompts) == 1

        prompt = prompts[0]
        assert prompt.name == "greeting-prompt"
        assert "{{#if formal}}" in prompt.template
        assert "{{else}}" in prompt.template
        assert "{{/if}}" in prompt.template
