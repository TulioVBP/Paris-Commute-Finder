import os

import googlemaps
import streamlit as st
from dotenv import load_dotenv
from streamlit_searchbox import st_searchbox

load_dotenv()

st.set_page_config(page_title="Paris Commute Finder", layout="wide")

st.title("Paris Commute Finder")
st.caption("Find neighborhoods reachable from all your work addresses within a time budget.")

# --- Session state ---
if "loc_ids" not in st.session_state:
    st.session_state.loc_ids = [0, 1]
    st.session_state.next_loc_id = 2
if "result" not in st.session_state:
    st.session_state.result = None
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None


def _make_address_searcher(api_key: str):
    """Return a search function that queries Google Places Autocomplete."""
    def search(query: str) -> list[str]:
        if not query or len(query) < 3:
            return []
        try:
            client = googlemaps.Client(key=api_key)
            preds = client.places_autocomplete(
                query,
                language="fr",
                components={"country": "fr"},
            )
            return [p["description"] for p in preds]
        except Exception:
            return []
    return search


# --- Sidebar ---
with st.sidebar:
    st.header("Settings")

    # API key — read from .env or let user paste it
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Google Maps API key", type="password")

    search_fn = _make_address_searcher(api_key) if api_key else lambda _: []

    st.subheader("Work destinations")
    to_remove = None
    selected_locations: dict[int, str | None] = {}
    for loc_id in st.session_state.loc_ids:
        idx = st.session_state.loc_ids.index(loc_id)
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            val = st_searchbox(
                search_fn,
                key=f"addr_{loc_id}",
                placeholder=f"Destination {idx + 1} — start typing…",
            )
            selected_locations[loc_id] = val
        with col_btn:
            if len(st.session_state.loc_ids) > 1 and st.button("✕", key=f"rm_{loc_id}"):
                to_remove = loc_id

    if to_remove is not None:
        st.session_state.loc_ids.remove(to_remove)
        st.rerun()

    if len(st.session_state.loc_ids) < 5:
        if st.button("＋ Add destination"):
            st.session_state.loc_ids.append(st.session_state.next_loc_id)
            st.session_state.next_loc_id += 1
            st.rerun()

    st.divider()

    max_time = st.slider("Max commute time (min)", min_value=15, max_value=90, value=45, step=5)
    mode = st.selectbox("Transport mode", ["transit", "walking", "bicycling"])

    st.divider()
    run = st.button("Find Areas", type="primary", use_container_width=True)


# --- Run analysis ---
if run:
    locations = [v for v in selected_locations.values() if v]
    if not locations:
        st.error("Enter and select at least one destination from the suggestions.")
    elif not api_key:
        st.error("A Google Maps API key is required.")
    else:
        from commute_finder.runner import run_analysis

        progress = st.empty()
        log_lines: list[str] = []

        def log(msg: str) -> None:
            log_lines.append(msg)
            progress.code("\n".join(log_lines))

        try:
            reachable, output_path, communes, destinations = run_analysis(
                locations=locations,
                max_time=max_time,
                mode=mode,
                api_key=api_key,
                log=log,
            )
            st.session_state.result = (reachable, output_path, max_time)
            st.session_state.analysis_data = (communes, destinations, mode, output_path)
            progress.empty()
        except ValueError as e:
            progress.empty()
            st.error(str(e))
        except Exception as e:
            progress.empty()
            st.error(f"Unexpected error: {e}")


# --- Auto-rebuild map when max_time slider changes ---
if st.session_state.result and st.session_state.analysis_data:
    _, _, result_max_time = st.session_state.result
    if max_time != result_max_time:
        from commute_finder.runner import rebuild_for_limit
        communes, destinations, saved_mode, output_path = st.session_state.analysis_data
        reachable, output_path = rebuild_for_limit(communes, destinations, max_time, saved_mode, output_path)
        st.session_state.result = (reachable, output_path, max_time)


# --- Display results ---
if st.session_state.result:
    reachable, output_path, result_max_time = st.session_state.result

    if not reachable:
        st.warning("No areas found within budget. Try increasing the max commute time.")
    else:
        st.success(f"{len(reachable)} area(s) within {result_max_time} min from all destinations.")

        if os.path.exists(output_path):
            with open(output_path, encoding="utf-8") as f:
                map_html = f.read()
            st.components.v1.html(map_html, height=560)

        paris = sorted(
            [c for c in reachable if c["code"].startswith("75")],
            key=lambda c: c.get("max_travel_time") or 0,
        )
        outside = sorted(
            [c for c in reachable if not c["code"].startswith("75")],
            key=lambda c: c.get("max_travel_time") or 0,
        )

        def _table_rows(items: list[dict]) -> list[dict]:
            rows = []
            for c in items:
                t = c.get("max_travel_time")
                by_dest = {k: (f"{v // 60} min" if v else "—") for k, v in c.get("travel_times_by_dest", {}).items()}
                row = {"Area": c["nom"], "Worst commute": f"{t // 60} min" if t else "—"}
                row.update(by_dest)
                rows.append(row)
            return rows

        col_paris, col_outside = st.columns(2)
        with col_paris:
            st.subheader("In Paris")
            if paris:
                st.dataframe(_table_rows(paris), use_container_width=True, hide_index=True)
            else:
                st.caption("No Paris neighborhoods within budget.")
        with col_outside:
            st.subheader("Out of Paris")
            if outside:
                st.dataframe(_table_rows(outside), use_container_width=True, hide_index=True)
            else:
                st.caption("No suburbs within budget.")
