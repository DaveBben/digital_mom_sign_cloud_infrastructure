from typing import Any, Dict
import logging
import os
import json
import boto3
import random
import base64
import datetime

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))

MAX_SECONDS_DELTA = 60 * 60 * 24  # one day


def main(event: Dict, context: Any):
    """ """
    dynamo_client = boto3.client("dynamodb")
    table_name = os.environ["IOT_TABLE_NAME"]
    sns_topic_arn = os.environ["DEVICE_OFFLINE_TOPIC"]
    rule_name = os.environ["RULE_NAME"]
    try:
        recent_status = dynamo_client.get_item(
            ConsistentRead=True,
            TableName=table_name,
            Key={"device_name": {"S": "esp32c3_photo_frame"}},
        )
        if recent_status["Item"]["payload"]["M"]["eventType"]["S"] == "connected":
            LOGGER.info("Device connected, sending message")
            iot_client = boto3.client("iot-data")
            iot_client.publish(topic="new_image_available")
        else:
            last_connected_time = datetime.datetime.fromtimestamp(
                int(recent_status["Item"]["payload"]["M"]["timestamp"]["N"])
                / 1000  # from milliseconds to seconds
            )
            LOGGER.info(f"Last connected time was {last_connected_time}")
            now = datetime.datetime.now()
            delta = now - last_connected_time
            seconds = delta.total_seconds()
            LOGGER.info(f"Disconnected for {seconds} seconds")
            if seconds > MAX_SECONDS_DELTA:
                sns_client = boto3.client("sns")
                events_client = boto3.client('events')
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Message=f"Device offline as of {last_connected_time}. Rule disabled and must be manually re-enabled.", # noqa
                )
                events_client.disable_rule(
                    Name=rule_name
                )

    except Exception as ex:
        LOGGER.error(ex, exc_info=True)
