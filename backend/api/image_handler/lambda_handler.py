from typing import Any, Dict
import logging
import os
import json
import boto3
import random
import base64

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))


def get_all_files_from_bucket(bucket_name: str, prefix: str):
    s3_client = boto3.client("s3")
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    if "Contents" not in response:
        raise FileNotFoundError()
    files = response["Contents"]
    while "NextContinuationToken" in response:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            ContinuationToken=response["NextContinuationToken"],
        )
        files.extend(response["Contents"])
    # remove folder keys themselves
    files = list(filter(lambda f: f["Size"] > 0, files))
    return files


def download_file_from_s3(bucket_name: str, key_path: str):
    s3_client = boto3.client("s3")
    try:
        content_object = s3_client.get_object(Bucket=bucket_name, Key=key_path)
        data = content_object["Body"].read()
        length = content_object["ContentLength"]
        return {"data": data, "length": length}
    except Exception as ex:
        LOGGER.error(ex)


def main(event: Dict, context: Any):
    """ """
    try:
        s3_bucket_name = os.environ["S3_BUCKET_NAME"]
        s3_files = get_all_files_from_bucket(
            bucket_name=s3_bucket_name, prefix="public"
        )
        LOGGER.info(s3_files)
        random_num = random.randint(0, len(s3_files) - 1)
        random_key = s3_files[random_num]["Key"]
        LOGGER.info(random_key)
        object_data = download_file_from_s3(
            bucket_name=s3_bucket_name, key_path=random_key
        )
        data = object_data["data"]
        content_length = object_data["length"]

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "image/jpeg",
                "Content-Length": content_length
            },
            "body": base64.b64encode(data).decode("utf-8"),
            "isBase64Encoded": True,
        }
    except FileNotFoundError:
        LOGGER.error("Bucket is empty")
