from unittest.mock import Mock

import pytest

from data_ingestion.thumbnails import save_images, save_images_threaded, get_image


@pytest.fixture
def mock_upload_file(monkeypatch):
    mock = Mock()
    monkeypatch.setattr("data_ingestion.thumbnails.upload_file", mock)
    return mock


def test_save_images(cleaned_recipes, mock_upload_file):
    save_images(df=cleaned_recipes)


def test_save_images_threaded(cleaned_recipes, mock_upload_file):
    save_images_threaded(df=cleaned_recipes, num_threads=2)


def test_get_image_faulty():
    image = get_image(image_url="https://faultylink.com/error", title="test")
    assert image is None
