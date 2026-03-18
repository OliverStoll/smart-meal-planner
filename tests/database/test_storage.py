import io
import pytest
from botocore.exceptions import ClientError
from unittest.mock import MagicMock

import database.storage as module


@pytest.fixture(autouse=True)
def mock_s3(monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(module, "s3_client", mock_client)
    return mock_client


def test_upload_file_calls_s3(monkeypatch, mock_s3):
    fake_file = io.BytesIO(b"data")
    module.upload_file(fake_file, "ref123")
    mock_s3.upload_fileobj.assert_called_once_with(fake_file, module.BUCKET_REF, "ref123")


def test_download_file_returns_buffer(mock_s3):
    content = b"testcontent"
    get_resp = {"Body": io.BytesIO(content)}
    mock_s3.get_object.return_value = get_resp

    result = module.download_file("ref456")
    assert result.read() == content
    assert result.name == "ref456"


def test_download_file_raises_if_client_none(monkeypatch):
    monkeypatch.setattr(module, "s3_client", None)
    with pytest.raises(RuntimeError):
        module.download_file("anything")


def test_file_exists_true(mock_s3):
    mock_s3.head_object.return_value = {}
    assert module.file_exists("exists_ref") is True


def test_file_exists_false(mock_s3):
    err = ClientError({"Error": {"Code": "404"}}, "HeadObject")
    mock_s3.head_object.side_effect = err
    assert module.file_exists("notfound") is False


def test_file_exists_other_error(mock_s3):
    err = ClientError({"Error": {"Code": "500"}}, "HeadObject")
    mock_s3.head_object.side_effect = err
    with pytest.raises(ClientError):
        module.file_exists("boom")


def test_download_thumbnail_handles_exceptions(mock_s3, monkeypatch):
    monkeypatch.setattr("database.storage.id_to_title", lambda x: "test-title")
    mock_s3.get_object.side_effect = Exception("fail")
    assert module.download_thumbnail(123) is None


def test_download_pdf_sets_name(mock_s3, monkeypatch):
    name = "recipe-title"
    monkeypatch.setattr("database.storage.id_to_title", lambda x: name)
    fake_body = io.BytesIO(b"pdfdata")
    mock_s3.get_object.return_value = {"Body": fake_body}
    result = module.download_pdf(42, num_portions=2)
    assert result.name == name
