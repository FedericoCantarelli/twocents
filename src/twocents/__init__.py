import click

from twocents.commands.rates import rates
from twocents.commands.version import version


@click.group()
def main():
    """ST: A command line tool for creating Structurizr themes easily."""


main.add_command(version)
main.add_command(rates)

if __name__ == "main":
    main()
