# NatuurSpotter

**NatuurSpotter** is a Python library for collecting and analysing moth observation data in **West Flanders, Belgium**.
It pulls public data from [waarnemingen.be](https://waarnemingen.be) and produces CSV biodiversity summaries, interactive HTML maps, species PDF reports, and seasonal charts — with an optional LLM-powered ecological explanation.

[![PyPI version](https://img.shields.io/pypi/v/natuurspotter)](https://pypi.org/project/natuurspotter/)
[![Python versions](https://img.shields.io/pypi/pyversions/natuurspotter)](https://pypi.org/project/natuurspotter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/mintyfizz/NatuurSpotter-1/actions/workflows/ci.yml/badge.svg)](https://github.com/mintyfizz/NatuurSpotter-1/actions/workflows/ci.yml)

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Output Files](#output-files)
- [Function Reference](#function-reference)
- [Notes](#notes)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- Scrape day-by-day moth observations for West Flanders
- Generate monthly biodiversity summaries (CSV) with Shannon/Simpson diversity indices
- Build interactive observation maps (HTML) with per-species colour coding
- Create species PDF reports with image, description, rarity status, and recent observations
- Run seasonal analysis with bar charts and an optional LLM ecological explanation

---

## Installation

Install from [PyPI](https://pypi.org/project/natuurspotter/) using pip:

```bash
pip install --upgrade natuurspotter
```

To include the optional LLM explanation feature:

```bash
pip install --upgrade "natuurspotter[llm]"
```

**Requires Python 3.9 or newer.**

---

## Configuration

NatuurSpotter reads API keys from environment variables. Create a `.env` file in your project directory:

```env
GEOAPIFY_API_KEY=your_key_here      # required for observations_map()
TOGETHER_API_KEY=your_key_here      # optional — only for LLM feature in seasonal_analysis()
```

| Key | Required | Purpose | Get one at |
|-----|----------|---------|------------|
| `GEOAPIFY_API_KEY` | Yes (for maps) | Geocoding observation locations | [geoapify.com](https://www.geoapify.com/) |
| `TOGETHER_API_KEY` | No | LLM ecological explanation | [together.ai](https://www.together.ai/) |

Keys are never hard-coded and are loaded automatically via [`python-dotenv`](https://pypi.org/project/python-dotenv/).

---

## Quick Start

```python
from natuurspotter import biodiversity_analysis, observations_map, species_info, seasonal_analysis

# Monthly biodiversity CSV — saved to ./output/
summary_df, raw_df = biodiversity_analysis(month=1, year=2025)

# Interactive observation map for a single day — saved to ./output/
map_path = observations_map(day="2025-01-22")

# PDF species report — saved to ./output/
species_info("Agrotis segetum")

# Seasonal bar chart + optional LLM explanation (requires TOGETHER_API_KEY)
seasonal_analysis("Agrotis segetum", 2025)
```

All output is written to an `output/` folder in your current working directory.

---

## Output Files

| Function | Output file |
|----------|-------------|
| `biodiversity_analysis()` | `output/biodiversity_summary_<year>-<month>.csv` |
| `biodiversity_analysis()` | `output/biodiversity_raw_<year>-<month>.csv` |
| `observations_map()` | `output/observations_map_<date>.html` |
| `species_info()` | `output/<species_name>.pdf` |

---

## Function Reference

### `biodiversity_analysis(month, year, request_delay=0.2)`

Scrapes all moth observations for the given month and year in West Flanders.
Returns `(summary_df, raw_df)` and writes two CSV files to `output/`.

```python
summary_df, raw_df = biodiversity_analysis(month=3, year=2025)
print(summary_df[["species_richness", "shannon_diversity"]])
```

The summary CSV includes: total observations, species richness, unique locations, most-observed species, Shannon diversity index, and Simpson diversity index.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `month` | `int` | — | Month number (1–12) |
| `year` | `int` | — | Four-digit year |
| `request_delay` | `float` | `0.2` | Seconds between HTTP requests |

---

### `observations_map(day, open_browser=False, geocode_delay=0.1)`

Generates an interactive Folium map of all moth observations for a given date.
Returns the path to the saved HTML file, or `None` if no data is available.

```python
map_path = observations_map(day="2025-06-15")
```

Requires `GEOAPIFY_API_KEY`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `day` | `str` | — | Date in `YYYY-MM-DD` format |
| `open_browser` | `bool` | `False` | Open the map in a browser after saving |
| `geocode_delay` | `float` | `0.1` | Seconds between geocoding requests |

---

### `species_info(latinName)`

Fetches species information from waarnemingen.be and Wikipedia, then writes a PDF report
with an image, description, rarity status, and a table of recent West Flanders observations.

```python
species_info("Agrotis segetum")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `latinName` | `str` | Latin (scientific) species name |

---

### `seasonal_analysis(species, year)`

Plots a seasonal bar chart of observation counts for a species in West Flanders.
If `TOGETHER_API_KEY` is set, also prints a short LLM-generated ecological explanation.

```python
seasonal_analysis("Agrotis segetum", 2025)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `species` | `str` | Latin (scientific) species name |
| `year` | `int` | Four-digit year |

---

## Notes

- Observation data comes from [waarnemingen.be](https://waarnemingen.be). If the site's HTML structure changes, scraping functions may need updates.
- Geographic filtering is restricted to West Flanders (province code `15`).
- API keys are read from environment variables and never hard-coded.

---

## Contributing

Contributions are welcome. Please open an issue or pull request on [GitHub](https://github.com/mintyfizz/NatuurSpotter-1).
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

Distributed under the [MIT License](LICENSE).
