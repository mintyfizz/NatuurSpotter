# NatuurSpotter

NatuurSpotter is a Python package for collecting and analysing public moth observation data from
[waarnemingen.be](https://waarnemingen.be), focused on West Flanders, Belgium.

It can create biodiversity summary CSV files, interactive observation maps, species PDF reports, and seasonal
observation charts. An optional LLM integration can add a short ecological interpretation to seasonal analyses.

[![PyPI version](https://img.shields.io/pypi/v/natuurspotter)](https://pypi.org/project/natuurspotter/)
[![Python versions](https://img.shields.io/pypi/pyversions/natuurspotter)](https://pypi.org/project/natuurspotter/)
[![CI](https://github.com/mintyfizz/NatuurSpotter/actions/workflows/ci.yml/badge.svg)](https://github.com/mintyfizz/NatuurSpotter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- Collect moth observations from waarnemingen.be for West Flanders.
- Generate monthly biodiversity summaries with species richness, Shannon diversity, and Simpson diversity.
- Save raw observation exports for downstream analysis.
- Build Folium HTML maps with geocoded observation points.
- Create PDF species reports with descriptions, images, rarity status, and recent observations.
- Plot seasonal observation patterns for a species.
- Optionally generate an LLM-based ecological explanation when a Together API key is configured.

## Installation

Install the package from PyPI:

```bash
python -m pip install natuurspotter
```

Install the optional LLM dependency only if you want `seasonal_analysis()` to produce an AI-generated explanation:

```bash
python -m pip install "natuurspotter[llm]"
```

NatuurSpotter requires Python 3.9 or newer.

Verify the installation:

```bash
python -c "import natuurspotter; print(natuurspotter.__version__)"
```

## Configuration

NatuurSpotter reads API keys from environment variables. For local development, place them in a `.env` file in your
working directory:

```env
GEOAPIFY_API_KEY=your_geoapify_key_here
TOGETHER_API_KEY=your_together_key_here
```

| Variable | Required | Used by | Purpose |
| --- | --- | --- | --- |
| `GEOAPIFY_API_KEY` | Only for maps | `observations_map()` | Geocodes observation locations through Geoapify. |
| `TOGETHER_API_KEY` | Optional | `seasonal_analysis()` | Enables the optional LLM ecological explanation. |

The package never requires API keys for installation. Keys are only needed when you call features that depend on
external services.

## Quick Start

```python
from natuurspotter import (
    biodiversity_analysis,
    observations_map,
    seasonal_analysis,
    species_info,
)

# Save monthly biodiversity summary and raw observation CSV files.
summary_df, raw_df = biodiversity_analysis(month=1, year=2025)

# Save an interactive HTML map for one observation day.
map_path = observations_map(day="2025-01-22")

# Save a species PDF report.
species_info("Agrotis segetum")

# Show a seasonal observation chart for a species.
seasonal_analysis("Agrotis segetum", 2025)
```

By default, generated files are written to an `output/` directory under the current working directory.

## Generated Files

| Function | Output |
| --- | --- |
| `biodiversity_analysis()` | `output/biodiversity_summary_<year>-<month>.csv` |
| `biodiversity_analysis()` | `output/biodiversity_raw_<year>-<month>.csv` |
| `observations_map()` | `output/observations_map_<date>.html` |
| `species_info()` | `output/<species_name>.pdf` |

## Recommended API

### `biodiversity_analysis(month, year, request_delay=0.2)`

Collects daily moth observations for a month, computes biodiversity metrics, saves CSV files, and returns
`(summary_df, raw_df)`.

```python
summary_df, raw_df = biodiversity_analysis(month=6, year=2025)
```

### `observations_map(day, open_browser=False, geocode_delay=0.1)`

Creates an interactive HTML map for observations on a single date. Returns the saved HTML path, or `None` when no
observations are available.

```python
map_path = observations_map(day="2025-06-15", open_browser=False)
```

This function requires `GEOAPIFY_API_KEY`.

### `species_info(latinName)`

Creates a PDF report for a species using its scientific name.

```python
species_info("Agrotis segetum")
```

### `seasonal_analysis(species, year)`

Plots seasonal observation counts for a species. If `TOGETHER_API_KEY` is set and the `llm` extra is installed, it
also prints a short ecological explanation.

```python
seasonal_analysis("Agrotis segetum", 2025)
```

## Operational Notes

- Observation data is scraped from waarnemingen.be. If the site changes its HTML structure, scraping functions may
  need updates.
- Geographic filtering is focused on West Flanders.
- Network-facing functions use a package User-Agent and request throttling where repeated requests are expected.
- `observations_map()` does not open a browser unless `open_browser=True` is passed.
- The package is intended for research, education, and lightweight ecological reporting workflows.

## Development

Clone the repository and install the package in editable mode with development tools:

```bash
git clone https://github.com/mintyfizz/NatuurSpotter.git
cd NatuurSpotter
python -m pip install -e ".[dev]"
```

Run the test suite and lint checks:

```bash
pytest
ruff check .
```

## Project Links

- PyPI: [https://pypi.org/project/natuurspotter/](https://pypi.org/project/natuurspotter/)
- Source: [https://github.com/mintyfizz/NatuurSpotter](https://github.com/mintyfizz/NatuurSpotter)
- Issues: [https://github.com/mintyfizz/NatuurSpotter/issues](https://github.com/mintyfizz/NatuurSpotter/issues)

## License

NatuurSpotter is distributed under the [MIT License](LICENSE).
