import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from natuurspotter import biodiversity_analysis, observations_map


def main():
    parser = argparse.ArgumentParser(description="Run NatuurSpotter helper commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    biodiversity_parser = subparsers.add_parser("biodiversity", help="Generate monthly biodiversity CSV files.")
    biodiversity_parser.add_argument("--month", type=int, default=None, help="Month number (1-12).")
    biodiversity_parser.add_argument("--year", type=int, default=None, help="Year, for example 2026.")

    map_parser = subparsers.add_parser("map", help="Generate an observations map HTML file.")
    map_parser.add_argument("--day", type=str, default=None, help="Date in YYYY-MM-DD.")

    args = parser.parse_args()
    os.chdir(PROJECT_ROOT)

    if args.command == "biodiversity":
        biodiversity_analysis(month=args.month, year=args.year)
        return

    if args.command == "map":
        observations_map(day=args.day)
        return


if __name__ == "__main__":
    main()
