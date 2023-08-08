from constructs import Construct
from dataclasses import dataclass
from aws_cdk import (
    aws_lambda,
    Duration,
    aws_secretsmanager,
    aws_apigateway,
    aws_logs,
    aws_wafv2,
    aws_s3,
    aws_dynamodb,
    aws_iot,
    aws_iam,
    aws_sns,
    aws_events,
    aws_events_targets,
)
import os

BASE_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class IOT(Construct):
    def __init__(self, scope: Construct, id_: str):
        super().__init__(scope, id_)

        # TODO: fill in details

        # table for storing recent connects/disconnects
        iot_table = aws_dynamodb.Table(
            self,
            "IOTConnectionTable",
            partition_key=aws_dynamodb.Attribute(
                name="device_name", type=aws_dynamodb.AttributeType.STRING
            ),
        )

        # sns for device offline
        topic = aws_sns.Topic(
            self,
            "DeviceOfflince",
            topic_name="device-offline",
            display_name="Device Offline for extened period of time",
        )

        rule = aws_events.Rule(
            self,
            "TriggerDeviceLambda",
            rule_name="Publish_New_Image_Topic",
            schedule=aws_events.Schedule.rate(Duration.minutes(15)),
        )

        # Handles MQTT Topic Events
        device_control_fn = aws_lambda.Function(
            self,
            "devicecontrol",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            environment={
                "IOT_TABLE_NAME": iot_table.table_name,
                "DEVICE_OFFLINE_TOPIC": topic.topic_arn,
                "RULE_NAME": "Publish_New_Image_Topic"
            },
            function_name="Device-Control",
            handler="lambda_handler.main",
            description="Publishes to MQTT topics",
            code=aws_lambda.Code.from_asset(
                os.path.join(BASE_FILE_PATH, "device_control")
            ),
            timeout=Duration.minutes(5),
        )

        iot_table.grant_read_write_data(device_control_fn.role)
        topic.grant_publish(device_control_fn.role)

        device_control_fn.role.add_to_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["iot:Publish", "sns:ListTopics"],
                resources=[
                    "*",
                ],
            )
        )

        rule.add_target(
            aws_events_targets.LambdaFunction(device_control_fn, retry_attempts=0)
        )

        # Not the best, but avoids circular dependency issue
        device_control_fn.role.add_to_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["events:*"],
                resources=[
                    "*",
                ],
            )
        )

        iot_role = aws_iam.Role(
            self,
            "IotRoleForDynamoDB",
            assumed_by=aws_iam.ServicePrincipal("iot.amazonaws.com"),
        )
        iot_table.grant_read_write_data(iot_role)

        aws_iot.CfnTopicRule(
            self,
            "LifecycleEvents",
            topic_rule_payload=aws_iot.CfnTopicRule.TopicRulePayloadProperty(
                actions=[
                    aws_iot.CfnTopicRule.ActionProperty(
                        dynamo_db=aws_iot.CfnTopicRule.DynamoDBActionProperty(
                            hash_key_field="device_name",
                            hash_key_value="esp32c3_photo_frame",
                            role_arn=iot_role.role_arn,
                            table_name=iot_table.table_name,
                        ),
                    )
                ],
                sql="SELECT * as event, timestamp, version, topic(4) as eventType, topic(5) as clientId FROM '$aws/events/presence/+/+' WHERE topic(4) = 'connected' or topic(4) = 'disconnected'",  # noqa
            ),
        )
