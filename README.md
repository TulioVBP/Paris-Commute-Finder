# Paris Commute Finder

Find Paris-region neighborhoods that are within your maximum commute time from **all** your destinations simultaneously — ideal for couples with different workplaces, or anyone balancing multiple regular commutes.

## How it works

1. You provide one or more commute destinations (work, airport, school, etc.) and a maximum travel time.
2. The tool fetches all Île-de-France communes (1,300+) and pre-filters to realistic candidates.
3. It queries the **Google Maps Distance Matrix API** to get actual transit/cycling/walking times.
4. It produces:
   - An **interactive HTML map** colored by worst-case commute time (green = well within budget, red = over limit)
   - A **ranked console list** of the best areas

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Google Maps API key
```

### Google Maps API key

Enable the following APIs in [Google Cloud Console](https://console.cloud.google.com/):
- **Geocoding API**
- **Distance Matrix API**

The $200/month free tier covers roughly 40 searches with 3 destinations and 150 candidate communes each.

## Usage

```bash
# A couple commuting to La Défense and Gare de Lyon, max 40 min
python main.py -l "La Défense, Paris" -l "Gare de Lyon, Paris" -t 40

# Single commute to CDG airport by transit
python main.py -l "Charles de Gaulle Airport" -t 45 --mode transit

# Cycling distance from two locations
python main.py -l "République, Paris" -l "Nation, Paris" -t 20 --mode bicycling

# Save map to a custom file
python main.py -l "Opéra, Paris" -l "Vincennes" -t 35 -o my_search.html
```

The generated `.html` file opens in any browser — click any commune for travel time details.

## Options

| Flag | Default | Description |
|---|---|---|
| `-l / --location` | required | Commute destination (repeat for multiple) |
| `-t / --max-time` | `45` | Max one-way commute time in minutes |
| `-m / --mode` | `transit` | `transit`, `walking`, or `bicycling` |
| `-o / --output` | `commute_map.html` | Output HTML filename |
| `--api-key` | env var | Google Maps API key (or set `GOOGLE_MAPS_API_KEY`) |

## Data sources

- **Commune boundaries**: [geo.api.gouv.fr](https://geo.api.gouv.fr) — downloaded once and cached in `data/communes_idf.geojson`
- **Travel times**: Google Maps Distance Matrix API (transit departure: next Monday 08:30)
