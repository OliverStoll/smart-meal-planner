from unittest.mock import Mock

import pytest

from pdf.download import save_all_pdfs, save_single_pdf, remove_recipes_with_faulty_pdfs


@pytest.fixture
def mock_upload_file(monkeypatch):
    mock = Mock()
    monkeypatch.setattr("pdf.download.upload_file", mock)
    return mock


@pytest.fixture
def mock_file_exists(monkeypatch):
    mock = Mock()
    monkeypatch.setattr("pdf.download.file_exists", mock)
    return mock


def test_save_all_pdfs(cleaned_recipes, mock_upload_file):
    save_all_pdfs(recipes=cleaned_recipes[:1])


def test_save_single_pdf(cleaned_recipes, mock_upload_file):
    save_single_pdf(url=cleaned_recipes.iloc[0]["pdf"], db_ref=".temp/testfile.pdf")


def test_remove_recipes_with_faulty_pdfs(cleaned_recipes, mock_file_exists):
    checked_recipes = remove_recipes_with_faulty_pdfs(cleaned_recipes)
    assert len(checked_recipes) == 4
