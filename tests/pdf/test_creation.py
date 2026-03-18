from unittest.mock import Mock

import pytest

from pdf.creation import create_pdfs, PdfCreator, create_pdfs_threaded


@pytest.fixture
def mock_upload_file(monkeypatch):
    mock = Mock()
    monkeypatch.setattr("pdf.creation.upload_file", mock)
    return mock


def test_create_pdfs(cleaned_recipes, mock_upload_file):
    create_pdfs(recipes=cleaned_recipes[:1], num_meals=1)


def test_create_pdf_with_text(cleaned_recipes, mock_upload_file):
    creator = PdfCreator()
    creator.create_pdf_with_text(cleaned_recipes.iloc[0], num_meals=1)


def test_create_pdfs_threaded(cleaned_recipes, mock_upload_file):
    create_pdfs_threaded(recipes=cleaned_recipes[:1], num_meals=[1], num_threads_per_mealsize=1)
