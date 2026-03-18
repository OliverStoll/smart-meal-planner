import os
from io import BytesIO
from logs.logs import create_logger
from botocore.exceptions import ClientError
from dotenv import load_dotenv

import boto3

from settings import BUCKET_REF
from database.ref import thumbnail_ref, pdf_ref
from messaging.utils import id_to_title

load_dotenv()
log = create_logger("File Storage")

try:
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.environ["STORAGE_ENDPOINT"],
        aws_access_key_id=os.environ["STORAGE_KEY_ID"],
        aws_secret_access_key=os.environ["STORAGE_APPLICATION_KEY"],
    )
except Exception:
    s3_client = None


def upload_file(path_or_obj: str | BytesIO, ref: str):
    if not s3_client:
        raise RuntimeError("S3 client not initialized for `upload_file`.")
    s3_client.upload_fileobj(path_or_obj, BUCKET_REF, ref)


def download_file(ref: str) -> BytesIO | None:
    """Download a file from S3 into a BytesIO buffer."""
    if not s3_client:
        raise RuntimeError("S3 client not initialized for `download_file`.")
    obj = s3_client.get_object(Bucket=BUCKET_REF, Key=ref)
    buffer = BytesIO(obj["Body"].read())
    buffer.name = ref.split("/")[-1]
    buffer.seek(0)
    return buffer


def file_exists(ref: str) -> bool:
    if not s3_client:
        raise RuntimeError("S3 client not initialized for `file_exists`.")
    try:
        s3_client.head_object(Bucket=BUCKET_REF, Key=ref)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def download_thumbnail(recipe_id: int) -> BytesIO | None:
    pdf_title = id_to_title(recipe_id)
    ref = thumbnail_ref(title=pdf_title)
    try:
        return download_file(ref=ref)
    except Exception:
        return None


def download_pdf(recipe_id: int, num_portions: int) -> BytesIO | None:
    title = id_to_title(recipe_id)
    ref = pdf_ref(title=title, num_portions=num_portions)
    try:
        pdf_file = download_file(ref=ref)
        pdf_file.name = title
        return pdf_file
    except Exception:
        return None
