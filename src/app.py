"""Sample file to demonstrate the usage of click."""
import click


def my_function(a: int, b: int) -> int:
    """Example Function."""
    return a + b


@click.group()
def main() -> None:
    """Required."""
    pass


@main.command()
@click.option("--a", type=int, required=True)
@click.option("--b", type=int, required=True)
def my_command(a: int, b: int) -> None:
    """Example Command."""
    print(f"my_function(a, b) = {my_function(a, b)}")


if __name__ == '__main__':
    main()
