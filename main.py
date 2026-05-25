#!/usr/bin/env python3
"""
Paris Commute Finder – CLI entry point.
For a graphical interface run: streamlit run app.py

Usage:
    python main.py -l "La Défense, Paris" -l "Gare de Lyon, Paris" -t 40
    python main.py -l "CDG Airport" -l "Opéra, Paris" -t 45 --mode transit
"""

import sys

import click
from dotenv import load_dotenv

from commute_finder.report import generate_report
from commute_finder.runner import run_analysis

load_dotenv()


@click.command()
@click.option(
    "--location", "-l",
    multiple=True,
    required=True,
    help="Commute destination (repeatable). E.g. -l 'La Défense' -l 'Gare du Nord'",
)
@click.option(
    "--max-time", "-t",
    default=45,
    show_default=True,
    help="Maximum one-way commute time in minutes.",
)
@click.option(
    "--mode", "-m",
    type=click.Choice(["transit", "walking", "bicycling"], case_sensitive=False),
    default="transit",
    show_default=True,
    help="Transport mode.",
)
@click.option(
    "--output", "-o",
    default=None,
    help="Output HTML map filename (default: output/YYMMDD_HHmm_commute_map.html).",
)
@click.option(
    "--api-key",
    envvar="GOOGLE_MAPS_API_KEY",
    required=True,
    help="Google Maps API key. Can also be set via GOOGLE_MAPS_API_KEY env var.",
)
def main(location: tuple[str, ...], max_time: int, mode: str, output: str | None, api_key: str) -> None:
    """Find Paris-region areas within MAX_TIME minutes of all your commute destinations."""
    click.echo("")
    click.echo("Paris Commute Finder")
    click.echo("=" * 42)
    click.echo(f"Destinations : {', '.join(location)}")
    click.echo(f"Max time     : {max_time} min  |  Mode: {mode}")
    click.echo("")

    try:
        reachable, output_path, *_ = run_analysis(
            locations=list(location),
            max_time=max_time,
            mode=mode,
            api_key=api_key,
            output=output,
            log=click.echo,
        )
    except ValueError as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)

    click.echo("")
    generate_report(reachable, list(location), max_time)
    click.echo("Open it in your browser to explore the results interactively.")


if __name__ == "__main__":
    main()
