import os
from io import BytesIO

from dotenv import load_dotenv

import boto3

load_dotenv()

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["STORAGE_ENDPOINT"],
    aws_access_key_id=os.environ["STORAGE_KEY_ID"],
    aws_secret_access_key=os.environ["STORAGE_APPLICATION_KEY"],
)


def upload_file(path_or_obj: str | BytesIO, reference: str):
    s3.upload_file(path_or_obj, "meal-bot", reference)
