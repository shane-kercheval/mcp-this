"""CLI tool for interacting with LLMs and MCP tools."""
import asyncio
import signal
import click
import sys
from sik_llms.mcp_manager import MCPClientManager
from sik_llms import (
    user_message,
    assistant_message,
    create_client,
    ReasoningAgent,
    ThinkingEvent,
    ToolPredictionEvent,
    ToolResultEvent,
    TextChunkEvent,
    ErrorEvent,
    TextResponse,
)


def signal_handler(sig, frame):  # noqa
    """Handle Ctrl+C properly."""
    click.echo("\nExiting chat.")
    sys.exit(0)


def print_tool_infos(tool_infos: list[dict]) -> None:
    """Print tool information in a formatted way."""
    click.echo("\n=== Available Tools ===\n")
    for i, tool_info in enumerate(tool_infos, 1):
        name = tool_info['name']
        server = tool_info['server']
        tool = tool_info['tool']
        click.echo(f"{i}. {name} (Server: {server})")
        click.echo(f"   Description: {tool.description.strip()}")
        if tool.parameters:
            click.echo("   Parameters:")
            for param in tool.parameters:
                param_type = param.param_type.__name__ if hasattr(param.param_type, '__name__') else str(param.param_type)  # noqa: E501
                required = "Required" if param.required else "Optional"
                click.echo(f"     - {param.name} ({param_type}, {required})")
        click.echo("")


async def reasoning_agent_chat(  # noqa: PLR0912
        manager: MCPClientManager,
        messages: list[dict],
        agent_mode: bool=True,
        model: str='gpt-4o-mini',
        temperature: float=0.1,
    ) -> str:
    """Handle chat using the reasoning agent or chat."""
    if agent_mode:
        agent = ReasoningAgent(
            model_name=model,
            tools=manager.get_tools(),
            max_iterations=15,
            temperature=temperature,
            generate_final_response=True,
        )
        response_text = ""
        streaming_final_response = False
        async for event in agent.stream(messages=messages):
            if isinstance(event, ThinkingEvent):
                if event.content:
                    click.echo(click.style(f"\n[THINKING]: {event.content}", fg='blue'))
            elif isinstance(event, ToolPredictionEvent):
                click.echo(click.style(f"\n[TOOL PREDICTION]: {event.name}({event.arguments})", fg='yellow'))  # noqa: E501
            elif isinstance(event, ToolResultEvent):
                click.echo(click.style(f"\n[TOOL RESULT]: {event.name}: {event.result}", fg='green'))  # noqa: E501
            elif isinstance(event, TextChunkEvent):
                if not streaming_final_response:
                    click.echo(click.style("\n[FINAL RESPONSE]:", fg='cyan', bold=True))
                    streaming_final_response = True
                click.echo(event.content, nl=False)
                response_text += event.content
            elif isinstance(event, ErrorEvent):
                click.echo(click.style(f"[ERROR]: {event.content}", fg='red', bold=True))
            elif isinstance(event, TextResponse):
                click.echo("\n")
                click.echo(click.style(f"Total Cost: {event.total_cost:.5f}", fg='magenta'))
                click.echo(click.style(f"Total Duration: {event.duration_seconds:.2f} seconds", fg='magenta'))  # noqa: E501
        return response_text

    # else: chat mode
    client = create_client(
        model_name=model,
        temperature=temperature,
    )
    response_text = ""
    async for event in client.stream(messages=messages):
        if hasattr(event, 'content') and event.content is not None:
            click.echo(event.content, nl=False)
        elif isinstance(event, TextResponse):
            click.echo("\n")
            click.echo(click.style(f"Total Cost: {event.total_cost:.5f}", fg='magenta'))
            click.echo(click.style(f"Total Duration: {event.duration_seconds:.2f} seconds", fg='magenta'))  # noqa: E501
            response_text = event.response
    return response_text


@click.command()
@click.option(
    '--mcp_config',
    required=True,
    type=click.Path(exists=True),
    help='Path to the MCP configuration file',
)
@click.option(
    '--model',
    default='gpt-4o-mini',
    help='Model name to use for the client',
)
@click.option('-tools', is_flag=True, help='Display available tools')
@click.option('-chat', is_flag=True, help='Start chat mode')
def cli(mcp_config: str, model: str, tools: bool, chat: bool) -> None:
    """CLI tool for interacting with language models and tools."""
    signal.signal(signal.SIGINT, signal_handler)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def run() -> None:
            async with MCPClientManager(configs=mcp_config) as manager:
                if tools:
                    tool_infos = manager.get_tool_infos()
                    print_tool_infos(tool_infos)
                    return
                if chat:
                    messages = []
                    agent_mode = False
                    click.echo(click.style("Chat mode started. Type 'q' or press Ctrl+C to quit.", fg='green', bold=True))  # noqa: E501
                    click.echo(click.style(f"Current mode: {'MCP Agent' if agent_mode else 'Chat'}", fg='green'))  # noqa: E501
                    click.echo(click.style("Toggle mode ('Chat' or 'MCP Agent') by typing '!m'", fg='green'))  # noqa: E501
                    while True:
                        try:
                            user_input = click.prompt("\nYou", prompt_suffix="> ")
                            if user_input.lower() in ('q', 'quit', 'exit'):
                                click.echo("Exiting chat. Goodbye!")
                                break
                            if user_input.lower() == '!m':
                                agent_mode = not agent_mode
                                mode_name = 'MCP Agent' if agent_mode else 'Chat'
                                click.echo(click.style(f"Switched to {mode_name} mode", fg='yellow', bold=True))  # noqa: E501
                                continue
                            messages.append(user_message(user_input))
                            click.echo("\nAI> ", nl=False)
                            response = await reasoning_agent_chat(
                                manager=manager,
                                messages=messages,
                                agent_mode=agent_mode,
                                model=model,
                            )
                            # Add AI response to messages
                            messages.append(assistant_message(response))
                        except KeyboardInterrupt:
                            click.echo("\nExiting chat. Goodbye!")
                            break
                        except Exception as e:
                            click.echo(click.style(f"\nError: {e!s}", fg='red', bold=True))
                # If neither tools nor chat is specified, show help
                if not (tools or chat):
                    ctx = click.get_current_context()
                    click.echo(ctx.get_help())
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        click.echo("\nOperation interrupted. Exiting...")
    except Exception as e:
        click.echo(click.style(f"Error: {e!s}", fg='red', bold=True))
        sys.exit(1)


if __name__ == "__main__":
    cli()
