import os
import boto3
import aws_cdk as cdk
from aws_cdk import Tags
from backend.component import Backend

app = cdk.App()
service_name = "PhotoFrameService"
account = os.getenv("CDK_DEFAULT_ACCOUNT")
region = os.getenv("CDK_DEFAULT_REGION")

# Component stack
Backend(
    app,
    service_name,
    stack_name=service_name,
    env={
        "account": account,
        "region": region,
    },
)


app.synth()
