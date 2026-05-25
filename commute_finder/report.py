import click


def generate_report(reachable: list[dict], destinations: list[dict], max_time_minutes: int) -> None:
    sep = "=" * 58
    click.echo(sep)
    click.echo(f"  AREAS WITHIN {max_time_minutes} MIN FROM ALL DESTINATIONS")
    click.echo(sep)

    if not reachable:
        click.echo("  No areas found. Try increasing --max-time or checking your locations.")
        return

    sorted_areas = sorted(reachable, key=lambda c: c.get("max_travel_time") or 0)
    shown = sorted_areas[:25]

    for area in shown:
        max_t = area.get("max_travel_time") or 0
        pop = area.get("population", 0)
        pop_str = f"  pop. {pop:,}" if pop else ""
        click.echo(f"\n  {area['nom']} ({area['code']}){pop_str}")
        click.echo(f"    Worst commute : {max_t // 60} min")
        for dest_name, t in area.get("travel_times_by_dest", {}).items():
            label = f"{t // 60} min" if t is not None else "no route"
            click.echo(f"    -> {dest_name}: {label}")

    remaining = len(sorted_areas) - len(shown)
    if remaining > 0:
        click.echo(f"\n  ... and {remaining} more area(s). See the map for the full picture.")
    click.echo()
