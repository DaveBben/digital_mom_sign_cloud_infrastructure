from typing import Any, Dict
import logging
import os
import uuid
import boto3
from AuthPolicy import Policy
from hmac import compare_digest

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))


def main(event: Dict, context: Any):
    """
    The lambda authorizers is a middleware
    which will be invoked from the API gateway
    for every request. If the reqest containts a
    valid verification token, it will be issued
    an IAM policy restricting the resources
    that it has access to.

    If the request contains an invalid token,
    a 401 will be returned.

    Parameters:
    event (dict): API Gateway Event

    returns:
    dict - IAM policy
    """
    api_token_name = os.environ["API_TOKEN_NAME"]
    secrets_client = boto3.client("secretsmanager")

    expected_token = secrets_client.get_secret_value(SecretId=api_token_name)[
        "SecretString"
    ]

    actual_token = event["headers"].get("x-api-token", "")
    if not compare_digest(expected_token, actual_token):
        LOGGER.warning("Mismatched Tokens")
        # This will return 401 unauthorized
        raise Exception("Unauthorized")

    tmp = event["methodArn"].split(":")
    apiGatewayArnTmp = tmp[5].split("/")
    awsAccountId = tmp[4]
    principalId = uuid.uuid4().hex

    policy = Policy.AuthPolicy(principalId, awsAccountId)
    policy.restApiId = apiGatewayArnTmp[0]
    policy.region = tmp[3]
    policy.stage = apiGatewayArnTmp[1]

    policy.allowMethod(Policy.HttpVerb.GET, "image")
    authResponse = policy.build()
    LOGGER.info(authResponse)

    return authResponse
