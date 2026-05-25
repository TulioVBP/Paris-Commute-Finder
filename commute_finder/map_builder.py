import folium


def _commute_color(max_travel_seconds: int | None, limit_seconds: int) -> str:
    """Map worst-case commute time to a hex color (green → red)."""
    if max_travel_seconds is None:
        return "#aaaaaa"
    ratio = max_travel_seconds / limit_seconds
    if ratio <= 0.60:
        return "#1a9850"
    if ratio <= 0.80:
        return "#66bd63"
    if ratio <= 0.95:
        return "#fee08b"
    if ratio <= 1.00:
        return "#f46d43"
    if ratio <= 1.25:
        return "#d73027"
    return "#8b0000"


def _summary_panel_html(reachable: list[dict], max_time: int, limit_seconds: int) -> str:
    paris = sorted(
        [c for c in reachable if c["code"].startswith("75")],
        key=lambda c: c.get("max_travel_time") or 0,
    )
    outside = sorted(
        [c for c in reachable if not c["code"].startswith("75")],
        key=lambda c: c.get("max_travel_time") or 0,
    )

    def rows_html(items: list[dict]) -> str:
        if not items:
            return '<tr><td colspan="2" style="color:#999;padding:4px 0">None within budget</td></tr>'
        html = ""
        for c in items:
            t = c.get("max_travel_time")
            mins = t // 60 if t is not None else None
            ratio = (t / limit_seconds) if t is not None else 1.0
            if ratio <= 0.60:
                color = "#1a9850"
            elif ratio <= 0.80:
                color = "#4a9e4a"
            elif ratio <= 1.00:
                color = "#c07000"
            else:
                color = "#c0392b"
            time_str = f"{mins} min" if mins is not None else "—"
            html += (
                f'<tr>'
                f'<td style="padding:3px 6px 3px 0;max-width:160px;overflow:hidden;'
                f'white-space:nowrap;text-overflow:ellipsis">{c["nom"]}</td>'
                f'<td style="padding:3px 0;text-align:right;color:{color};'
                f'font-weight:600;white-space:nowrap">{time_str}</td>'
                f'</tr>'
            )
        return html

    section_style = (
        "font-size:11px;font-weight:700;color:#555;text-transform:uppercase;"
        "letter-spacing:0.6px;margin:10px 0 5px"
    )

    return f"""
    <div id="summary-panel" style="position:fixed;top:10px;right:10px;z-index:1000;
         background:white;padding:14px 16px;border-radius:8px;
         box-shadow:2px 2px 10px rgba(0,0,0,0.20);font-size:13px;
         max-height:80vh;overflow-y:auto;min-width:230px;max-width:280px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <b style="font-size:14px">Top Areas – {max_time} min</b>
        <button onclick="document.getElementById('summary-panel').style.display='none'"
                style="border:none;background:none;cursor:pointer;font-size:18px;
                       color:#999;line-height:1;padding:0 0 0 8px">×</button>
      </div>
      <div style="{section_style}">In Paris</div>
      <table style="width:100%;border-collapse:collapse">{rows_html(paris)}</table>
      <div style="{section_style}">Out of Paris</div>
      <table style="width:100%;border-collapse:collapse">{rows_html(outside)}</table>
    </div>
    """


def build_map(
    communes: list[dict],
    reachable: list[dict],
    destinations: list[dict],
    max_time_minutes: int,
    mode: str,
    output_path: str,
) -> None:
    limit_seconds = max_time_minutes * 60

    center_lat = sum(d["lat"] for d in destinations) / len(destinations)
    center_lng = sum(d["lng"] for d in destinations) / len(destinations)

    m = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles="CartoDB positron")

    # Commune polygons
    for commune in communes:
        if not commune.get("geometry"):
            continue
        max_travel = commune.get("max_travel_time")
        color = _commute_color(max_travel, limit_seconds)

        popup_lines = [f"<b>{commune['nom']}</b>"]
        if commune.get("population"):
            popup_lines.append(f"Population : {commune['population']:,}")
        for dest_name, t in commune.get("travel_times_by_dest", {}).items():
            label = f"{t // 60} min" if t is not None else "no route"
            popup_lines.append(f"&#8594; {dest_name}: {label}")
        popup_html = "<br>".join(popup_lines)

        folium.GeoJson(
            commune["geometry"],
            style_function=lambda _feat, c=color: {
                "fillColor": c,
                "color": "#666666",
                "weight": 0.4,
                "fillOpacity": 0.70,
            },
            tooltip=folium.Tooltip(commune["nom"], sticky=False),
            popup=folium.Popup(popup_html, max_width=260),
        ).add_to(m)

    # Destination markers
    for dest in destinations:
        folium.Marker(
            location=[dest["lat"], dest["lng"]],
            tooltip=dest["name"],
            popup=folium.Popup(f"<b>{dest['name']}</b>", max_width=200),
            icon=folium.Icon(color="blue", icon="map-marker", prefix="fa"),
        ).add_to(m)

    # Legend
    half = max_time_minutes // 2
    pct80 = int(max_time_minutes * 0.80)
    pct95 = int(max_time_minutes * 0.95)
    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:14px 18px;border-radius:8px;
                box-shadow:2px 2px 8px rgba(0,0,0,0.25);font-size:13px;line-height:1.7">
      <b>Worst commute – {mode} &nbsp;(max {max_time_minutes} min)</b><br>
      <span style="background:#1a9850;display:inline-block;width:14px;height:14px;margin-right:6px;border-radius:3px;vertical-align:middle"></span>&le;&nbsp;{half} min<br>
      <span style="background:#66bd63;display:inline-block;width:14px;height:14px;margin-right:6px;border-radius:3px;vertical-align:middle"></span>&le;&nbsp;{pct80} min<br>
      <span style="background:#fee08b;display:inline-block;width:14px;height:14px;margin-right:6px;border-radius:3px;vertical-align:middle"></span>&le;&nbsp;{pct95} min<br>
      <span style="background:#f46d43;display:inline-block;width:14px;height:14px;margin-right:6px;border-radius:3px;vertical-align:middle"></span>&le;&nbsp;{max_time_minutes} min<br>
      <span style="background:#d73027;display:inline-block;width:14px;height:14px;margin-right:6px;border-radius:3px;vertical-align:middle"></span>over limit<br>
      <span style="background:#aaaaaa;display:inline-block;width:14px;height:14px;margin-right:6px;border-radius:3px;vertical-align:middle"></span>no route found
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Summary panel (top-right)
    m.get_root().html.add_child(folium.Element(_summary_panel_html(reachable, max_time_minutes, limit_seconds)))

    m.save(output_path)
