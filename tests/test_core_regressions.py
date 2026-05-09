from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image

from natuurspotter import core


class FakeResponse:
    def __init__(self, text="", json_data=None, content=b""):
        self.text = text
        self._json_data = json_data
        self.content = content

    def json(self):
        return self._json_data


class CoreRegressionTests(unittest.TestCase):
    def make_image_bytes(self, image_format="PNG"):
        image = Image.new("RGB", (1, 1), (255, 0, 0))
        output = BytesIO()
        image.save(output, format=image_format)
        return output.getvalue()

    def test_getspecies_name_uses_raw_latin_query_without_translation(self):
        urls = []

        def fake_get(url, **kwargs):
            urls.append(url)
            return FakeResponse("<li class='lead'><a href='/species/123/agrotis-segetum'>Agrotis segetum</a></li>")

        with patch.object(core, "_http_get", side_effect=fake_get), patch.object(
            core,
            "_translate_text",
            side_effect=AssertionError("Latin names must not be translated"),
        ):
            link = core.getspecies_name("Agrotis segetum")

        self.assertEqual(link, "https://waarnemingen.be/species/123/agrotis-segetum/")
        self.assertIn("q=Agrotis+segetum", urls[0])

    def test_getrarity_fetches_species_page_once(self):
        species_url = "https://waarnemingen.be/species/123/agrotis-segetum/"
        calls = []

        species_html = """
        <html>
            <div><span class="hidden-sm">Rare</span></div>
            <i class="species-scientific-name">Agrotis segetum</i>
            <span class="species-common-name">Turnip moth</span>
        </html>
        """
        observations_html = """
        <table class="table">
            <tbody>
                <tr><td>2026-01-01</td><td>3 observations</td><td>Brugge</td></tr>
            </tbody>
        </table>
        """

        def fake_get(url, **kwargs):
            calls.append(url)
            if url == species_url:
                return FakeResponse(species_html)
            if url.startswith(f"{species_url}observations/"):
                return FakeResponse(observations_html)
            raise AssertionError(f"Unexpected URL: {url}")

        with patch.object(core, "getspecies_name", return_value=species_url), patch.object(
            core,
            "_http_get",
            side_effect=fake_get,
        ):
            common_name, scientific_name, rarity_status, observations = core.getRarity("Agrotis segetum")

        self.assertEqual(calls.count(species_url), 1)
        self.assertEqual(common_name, "Turnip moth")
        self.assertEqual(scientific_name, "Agrotis segetum")
        self.assertEqual(rarity_status, "Rare")
        self.assertEqual(observations.iloc[0].to_dict(), {"date": "2026-01-01", "number": "3", "location": "Brugge"})

    def test_getrarity_returns_none_when_species_is_missing(self):
        with patch.object(core, "getspecies_name", return_value=""):
            self.assertIsNone(core.getRarity("Missing species"))

    def test_observations_map_empty_data_returns_none_without_opening_browser(self):
        with patch.object(core, "Sdata", return_value=[]), patch.object(
            core.webbrowser,
            "open",
            side_effect=AssertionError("browser should not open"),
        ):
            self.assertIsNone(core.observations_map("2026-01-01"))

    def test_observations_map_escapes_species_html(self):
        species = "<script>alert(1)</script>"

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(core.os, "getcwd", return_value=tmpdir), patch.object(
            core,
            "Sdata",
            return_value=[{"date": "2026-01-01", "species": species, "location": "Brugge", "sum": 1}],
        ), patch.object(
            core,
            "rowstopoints",
            return_value=[{"date": "2026-01-01", "species": species, "location": "Brugge", "lat": 51.2, "lng": 3.2}],
        ):
            path = core.observations_map("2026-01-01")
            content = Path(path).read_text(encoding="utf-8")

        self.assertNotIn(species, content)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", content)

    def test_rowstopoints_keeps_uppercase_location_names(self):
        seen_locations = []

        def fake_geopoints(location):
            seen_locations.append(location)
            return 51.0, 3.0

        rows = [{"date": "2026-01-01", "species": "Species", "location": "ABCD (WV)"}]
        with patch.object(core, "geopoints", side_effect=fake_geopoints), patch.object(core, "wV", return_value=True):
            points = core.rowstopoints(rows, geocode_delay=0)

        self.assertEqual(seen_locations, ["ABCD"])
        self.assertEqual(points[0]["location"], "ABCD")

    def test_rowstopoints_throttles_geocoding_requests(self):
        rows = [{"date": "2026-01-01", "species": "Species", "location": "Brugge, Kortrijk"}]

        with patch.object(core, "geopoints", return_value=(51.0, 3.0)), patch.object(
            core,
            "wV",
            return_value=True,
        ), patch.object(core.time, "sleep") as sleep:
            points = core.rowstopoints(rows, geocode_delay=0.5)

        self.assertEqual(len(points), 2)
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_any_call(0.5)

    def test_season_stops_before_adding_duplicate_page(self):
        calls = []
        table_html = """
        <div class="table-container">
            <table>
                <tbody>
                    <tr><td>2026-01-01</td><td>5 observations</td></tr>
                </tbody>
            </table>
        </div>
        """

        def fake_get(url, **kwargs):
            calls.append(url)
            return FakeResponse(table_html)

        with patch.object(core, "_http_get", side_effect=fake_get):
            data = core.season(2026, "123", request_delay=0)

        self.assertEqual(len(calls), 2)
        self.assertEqual(len(data), 1)
        self.assertEqual(int(data.iloc[0]["count"]), 5)

    def test_season_throttles_paginated_requests(self):
        responses = [
            """
            <div class="table-container"><table><tbody>
                <tr><td>2026-01-01</td><td>5 observations</td></tr>
            </tbody></table></div>
            """,
            """
            <div class="table-container"><table><tbody>
                <tr><td>2026-02-01</td><td>7 observations</td></tr>
            </tbody></table></div>
            """,
            "<html></html>",
        ]

        def fake_get(url, **kwargs):
            return FakeResponse(responses.pop(0))

        with patch.object(core, "_http_get", side_effect=fake_get), patch.object(core.time, "sleep") as sleep:
            data = core.season(2026, "123", request_delay=0.25)

        self.assertEqual(len(data), 2)
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_any_call(0.25)

    def test_speciescolor_palette_uses_six_digit_hex_colors(self):
        colors = {}

        for index in range(100):
            color = core.speciescolor(f"Species {index}", colors)
            self.assertRegex(color, r"^#[0-9a-fA-F]{6}$")

    def test_pdf_image_bytes_converts_tiff_to_png(self):
        suffix, image_bytes = core._pdf_image_bytes("https://example.test/image.tiff", self.make_image_bytes("TIFF"))

        self.assertEqual(suffix, ".png")
        self.assertTrue(image_bytes.startswith(b"\x89PNG"))

    def test_species_info_deletes_temp_image_when_pdf_image_fails(self):
        image_paths = []

        class RaisingPDF:
            def __init__(self):
                self.w = 210
                self.l_margin = 10
                self.r_margin = 10

            def set_auto_page_break(self, **kwargs):
                pass

            def add_page(self):
                pass

            def add_font(self, *args, **kwargs):
                pass

            def set_font(self, *args, **kwargs):
                pass

            def cell(self, *args, **kwargs):
                pass

            def ln(self, *args, **kwargs):
                pass

            def image(self, path, **kwargs):
                image_paths.append(path)
                raise RuntimeError("PDF image failed")

            def multi_cell(self, *args, **kwargs):
                pass

            def output(self, *args, **kwargs):
                pass

        with patch.object(core, "FPDF", RaisingPDF), patch.object(
            core,
            "getinfo",
            return_value="description",
        ), patch.object(
            core,
            "get_image",
            return_value=("https://example.test/image.png", self.make_image_bytes("PNG")),
        ), patch.object(
            core,
            "getRarity",
            return_value=("Common", "Scientific", "Rare", pd.DataFrame()),
        ):
            with self.assertRaises(RuntimeError):
                core.species_info("Agrotis segetum")

        self.assertEqual(len(image_paths), 1)
        self.assertFalse(Path(image_paths[0]).exists())

    def test_observationtble_parses_rows_and_derives_seasons(self):
        table_html = """
        <table>
            <tbody>
                <tr><td>Observed on 2026-01-15</td><td>7 observations</td></tr>
                <tr><td>Observed on 2026-07-03</td><td>12 observations</td></tr>
            </tbody>
        </table>
        """
        table = BeautifulSoup(table_html, "html.parser").find("table")

        rows = core.observationtble(table)

        self.assertEqual(rows, [
            {"date": "2026-01-15", "count": 7, "season": "Winter"},
            {"date": "2026-07-03", "count": 12, "season": "Summer"},
        ])

    def test_seasonal_analysis_notebook_path_skips_llm_without_key(self):
        season_df = pd.DataFrame({
            "date": pd.to_datetime(["2026-01-01", "2026-06-01"]),
            "count": [2, 5],
            "season": ["Winter", "Summer"],
        })

        with patch.object(core, "getspecies_name", return_value="https://waarnemingen.be/species/123/test/"), patch.object(
            core,
            "season",
            return_value=season_df,
        ) as season_call, patch.object(core.os, "getenv", return_value=""), patch.object(core.plt, "show") as show, patch(
            "builtins.print"
        ) as printed:
            result = core.seasonal_analysis("Koolbladroller", 2026)

        self.assertIsNone(result)
        season_call.assert_called_once_with(2026, "123")
        show.assert_called_once()
        printed.assert_any_call("TOGETHER_API_KEY not set, skipping LLM explanation.")

    def test_seasonal_analysis_notebook_path_reports_missing_species(self):
        with patch.object(core, "getspecies_name", return_value=""), patch("builtins.print") as printed:
            result = core.seasonal_analysis("Unknown species", 2026)

        self.assertIsNone(result)
        printed.assert_any_call("species not found")

    def test_biodiversity_empty_branch_prints_saved_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.object(core.os, "getcwd", return_value=tmpdir), patch.object(
            core,
            "Sdata",
            return_value=[],
        ), patch.object(core.time, "sleep"), patch("builtins.print") as printed:
            summary_df, raw_df = core.biodiversity_analysis(month=1, year=2026, request_delay=0)

        self.assertTrue(raw_df.empty)
        self.assertEqual(int(summary_df.iloc[0]["totalObservations"]), 0)
        printed.assert_any_call("Saved summary CSV:", str(Path(tmpdir) / "output" / "biodiversity_summary_2026-01.csv"))
        printed.assert_any_call("Saved raw CSV:", str(Path(tmpdir) / "output" / "biodiversity_raw_2026-01.csv"))


if __name__ == "__main__":
    unittest.main()
