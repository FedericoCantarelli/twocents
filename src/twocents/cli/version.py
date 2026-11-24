import click

from twocents import __version__


@click.command()
def version():
    """Get CLI version."""
    click.echo(f"{click.style('2cents', bold=True)} v{__version__}")
