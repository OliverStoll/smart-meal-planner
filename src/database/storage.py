import os
from io import BytesIO

from botocore.exceptions import ClientError
from dotenv import load_dotenv

import boto3

load_dotenv()

BUCKET_REF = "meal-bot"

try:
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["STORAGE_ENDPOINT"],
        aws_access_key_id=os.environ["STORAGE_KEY_ID"],
        aws_secret_access_key=os.environ["STORAGE_APPLICATION_KEY"],
    )
except Exception:
    s3 = None


def upload_file(path_or_obj: str | BytesIO, ref: str):
    s3.upload_fileobj(path_or_obj, BUCKET_REF, ref)


def file_exists(ref: str) -> bool:
    try:
        s3.head_object(Bucket=BUCKET_REF, Key=ref)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise
