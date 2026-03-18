import pytest
import pandas as pd

from supermarkets.cleaning import clean_sellers, SUPERMARKET_FRIENDLY_NAMES

SAMPLE_CSV = """title,sellers
Milch,"ist bei Rewe und Lidl erhältlich"
Brot,"ist bei EDEKA erhältlich"
Käse,"ist bei Netto Marken-Discount und Kaufland erhältlich"
Wurst,"ist bei Aldi Nord erhältlich"
Nudeln,"ist bei Rewe und EDEKA und Lidl erhältlich"
Unbekannt,"ist bei UnbekannterLaden erhältlich"
Leer,
"""


@pytest.fixture
def sample_csv_path(tmp_path):
    csv_file = tmp_path / "product_data.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    return str(csv_file)


class TestCleanSellers:
    def test_returns_dataframe(self, sample_csv_path):
        result = clean_sellers(sample_csv_path)
        assert isinstance(result, pd.DataFrame)

    def test_sellers_always_column_exists(self, sample_csv_path):
        result = clean_sellers(sample_csv_path)
        assert "sellers_always" in result.columns

    def test_sellers_partially_column_exists(self, sample_csv_path):
        result = clean_sellers(sample_csv_path)
        assert "sellers_partially" in result.columns

    def test_rewe_mapped_to_friendly_name(self, sample_csv_path):
        result = clean_sellers(sample_csv_path)
        milch_row = result[result["title"] == "Milch"].iloc[0]
        assert "Rewe" in milch_row["sellers_always"]

    def test_lidl_mapped_to_friendly_name(self, sample_csv_path):
        result = clean_sellers(sample_csv_path)
        milch_row = result[result["title"] == "Milch"].iloc[0]
        assert "Lidl" in milch_row["sellers_always"]

    def test_edeka_mapped_to_friendly_name(self, sample_csv_path):
        result = clean_sellers(sample_csv_path)
        brot_row = result[result["title"] == "Brot"].iloc[0]
        assert "Edeka" in brot_row["sellers_always"]

    def test_aldi_nord_mapped_to_friendly_name(self, sample_csv_path):
        result = clean_sellers(sample_csv_path)
        wurst_row = result[result["title"] == "Wurst"].iloc[0]
        assert "Aldi" in wurst_row["sellers_always"]

    def test_empty_sellers_handled_gracefully(self, sample_csv_path):
        result = clean_sellers(sample_csv_path)
        leer_row = result[result["title"] == "Leer"].iloc[0]
        assert leer_row["sellers_always"] == ""


class TestSupermarketFriendlyNames:
    def test_contains_all_expected_supermarkets(self):
        expected = [
            "Netto Marken-Discount",
            "Kaufland",
            "EDEKA",
            "Lidl",
            "Aldi Nord",
            "Rewe",
        ]
        for name in expected:
            assert name in SUPERMARKET_FRIENDLY_NAMES

    def test_friendly_names_are_not_longer_than_originals(self):
        for original, friendly in SUPERMARKET_FRIENDLY_NAMES.items():
            assert len(friendly) <= len(original)
