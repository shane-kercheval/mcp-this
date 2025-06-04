#!/usr/bin/env python3
"""
Prompt definitions and parsing for MCP server.

This module handles the parsing and validation of prompt configurations
from YAML files, similar to how tools.py handles tool configurations.
"""
import re
from dataclasses import dataclass


@dataclass
class PromptArgument:
    """Represents an argument for a prompt."""

    description: str
    required: bool


@dataclass
class PromptInfo:
    """Represents a prompt with its metadata and arguments."""

    name: str
    description: str
    template: str
    arguments: dict[str, PromptArgument]


def validate_prompt_config(prompt_name: str, prompt_config: dict) -> None:
    """
    Validate a prompt configuration.

    Args:
        prompt_name: The name of the prompt.
        prompt_config: The prompt configuration dictionary.

    Raises:
        ValueError: If the prompt configuration is invalid.
    """
    if not isinstance(prompt_config, dict):
        raise ValueError(f"Prompt '{prompt_name}' must be a dictionary")

    if 'description' not in prompt_config:
        raise ValueError(f"Prompt '{prompt_name}' must contain a 'description'")

    if not isinstance(prompt_config['description'], str):
        raise ValueError(f"Prompt '{prompt_name}' description must be a string")

    if 'template' not in prompt_config:
        raise ValueError(f"Prompt '{prompt_name}' must contain a 'template'")

    if not isinstance(prompt_config['template'], str):
        raise ValueError(f"Prompt '{prompt_name}' template must be a string")

    # Arguments are optional
    if 'arguments' in prompt_config:
        if not isinstance(prompt_config['arguments'], dict):
            raise ValueError(f"Prompt '{prompt_name}' arguments must be a dictionary")

        for arg_name, arg_config in prompt_config['arguments'].items():
            validate_prompt_argument_config(prompt_name, arg_name, arg_config)


def validate_prompt_argument_config(prompt_name: str, arg_name: str, arg_config: dict) -> None:
    """
    Validate a prompt argument configuration.

    Args:
        prompt_name: The name of the prompt.
        arg_name: The name of the argument.
        arg_config: The argument configuration dictionary.

    Raises:
        ValueError: If the argument configuration is invalid.
    """
    # Validate argument name for Python identifier compatibility
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', arg_name):
        raise ValueError(
            f"Argument name '{arg_name}' in prompt '{prompt_name}' contains invalid characters. "
            "Argument names must be valid Python identifiers (letters, numbers, underscores, "
            "cannot start with a number).",
        )

    if not isinstance(arg_config, dict):
        raise ValueError(f"Argument '{arg_name}' in prompt '{prompt_name}' must be a dictionary")

    if 'description' not in arg_config:
        raise ValueError(
            f"Argument '{arg_name}' in prompt '{prompt_name}' must contain a 'description'",
        )

    if not isinstance(arg_config['description'], str):
        raise ValueError(
            f"Argument '{arg_name}' description in prompt '{prompt_name}' must be a string",
        )

    if 'required' not in arg_config:
        raise ValueError(
            f"Argument '{arg_name}' in prompt '{prompt_name}' must contain a 'required' field",
        )

    if not isinstance(arg_config['required'], bool):
        raise ValueError(
            f"Argument '{arg_name}' required field in prompt '{prompt_name}' must be a boolean",
        )


def parse_prompts(config: dict) -> list[PromptInfo]:
    """
    Parse prompt configurations from the config dictionary.

    Args:
        config: The configuration dictionary containing prompts.

    Returns:
        List of PromptInfo objects.

    Raises:
        ValueError: If the configuration is invalid.
    """
    prompts_info = []

    # Prompts section is optional
    if 'prompts' not in config:
        return prompts_info

    if not isinstance(config['prompts'], dict):
        raise ValueError("'prompts' must be a dictionary")

    for prompt_name, prompt_config in config['prompts'].items():
        validate_prompt_config(prompt_name, prompt_config)

        # Parse arguments
        arguments = {}
        if 'arguments' in prompt_config:
            for arg_name, arg_config in prompt_config['arguments'].items():
                arguments[arg_name] = PromptArgument(
                    description=arg_config['description'],
                    required=arg_config['required'],
                )

        prompt_info = PromptInfo(
            name=prompt_name,
            description=prompt_config['description'],
            template=prompt_config['template'],
            arguments=arguments,
        )

        prompts_info.append(prompt_info)

    return prompts_info
