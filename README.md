# NatuurSpotter

NatuurSpotter is a Python project for collecting and analyzing moth observation data in **West Flanders (Belgium)**.
It pulls public data from **waarnemingen.be** and can generate CSV summaries, interactive maps, seasonal charts, and PDF species reports.

## Features

- Scrape day-by-day moth observations for West Flanders
- Build monthly biodiversity summaries (`CSV`) for dashboards (including Node-RED)
- Generate interactive observation maps (`HTML`)
- Create species PDF reports with image, description, rarity, and recent observations
- Run seasonal analysis and (optionally) add an LLM-based ecological explanation

## Requirements

- Python 3.8 or newer
- Internet access (for waarnemingen.be, Wikimedia, Wikipedia, Geoapify, and optionally Together)

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

Install the optional Together dependency only when you need the LLM explanation in `seasonal_analysis`:

```bash
pip install -e ".[llm]"
# or, when using requirements.txt:
pip install "together>=2.0"
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys.

```bash
cp .env.example .env
```

Required for map/geocoding features:

- `GEOAPIFY_API_KEY`

Optional for LLM explanation in `seasonal_analysis`:

- `TOGETHER_API_KEY`

## Quick Usage

```python
from natuurspotter import biodiversity_analysis, observations_map, species_info, seasonal_analysis

# Monthly biodiversity CSV outputs in ./output/
summary_df, raw_df = biodiversity_analysis(month=1, year=2026)

# Interactive map in ./output/observations_map_YYYY-MM-DD.html
map_path = observations_map(day="2026-01-22")

# PDF species report in ./output/
species_info("Agrotis segetum")

# Seasonal chart + optional LLM explanation (if TOGETHER_API_KEY is set)
seasonal_analysis("Agrotis segetum", 2025)
```

## Script Usage

```bash
# Generate monthly biodiversity CSV files in ./output/
python3 scripts/run_natuurspotter.py biodiversity --month 1 --year 2026

# Generate daily observation map in ./output/
python3 scripts/run_natuurspotter.py map --day 2026-01-22
```

## Output Files

Generated files are written to `output/`:

- `biodiversity_summary_<year>-<month>.csv`
- `biodiversity_raw_<year>-<month>.csv`
- `observations_map_<date>.html`
- `<species_name>.pdf`

## Project Structure

```text
NatuurSpotter/
├── src/
│   └── natuurspotter/
│       ├── __init__.py
│       ├── core.py
│       └── fonts/
├── requirements.txt
├── pyproject.toml
├── scripts/
│   └── run_natuurspotter.py
├── examples/
│   ├── demo.ipynb
│   └── demo1.ipynb
├── integrations/
│   └── node-red/
│       └── node_red_flow.json
├── output/                  # generated files (git-ignored)
└── README.md
```

## Notes

- This project relies on external website/API responses. If a provider changes HTML/API format, parts of the scraper may need updates.
- API keys are read from environment variables; do not commit real keys.
- If keys were previously exposed, rotate them before publishing.

## License

MIT License. See `LICENSE`.
