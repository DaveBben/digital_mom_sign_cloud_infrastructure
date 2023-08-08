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
)
import os

BASE_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


@dataclass
class WafRule:
    name: str
    rule_name: str
    priority: int
    metric_name: str
    excluded_rules: list[str]


class API(Construct):
    def __init__(self, scope: Construct, id_: str, s3_bucket: aws_s3.Bucket):
        super().__init__(scope, id_)

        # TODO: fill in details

        # Secret for API Access
        api_secrets = aws_secretsmanager.Secret(
            self, "apiAccesssecret", secret_name="api-access-token"
        )

        # Handles Authorization from API Gateway
        api_authorizer_fn = aws_lambda.Function(
            self,
            "APIAuthorizer",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            environment={"API_TOKEN_NAME": api_secrets.secret_name},
            function_name="API-Authorizer",
            handler="lambda_handler.main",
            description="Function that authorizers requests to Lambda API",
            code=aws_lambda.Code.from_asset(os.path.join(BASE_FILE_PATH, "authorizer")),
            timeout=Duration.minutes(5),
        )
        api_secrets.grant_read(api_authorizer_fn.role)

        photo_handler_fn = aws_lambda.Function(
            self,
            "PhotoHandler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            function_name="Photo-handler",
            environment={"S3_BUCKET_NAME": s3_bucket.bucket_name},
            handler="lambda_handler.main",
            description="Retrieves Photo from S3",
            code=aws_lambda.Code.from_asset(
                os.path.join(BASE_FILE_PATH, "image_handler")
            ),
            timeout=Duration.minutes(5),
        )
        s3_bucket.grant_read(photo_handler_fn.role)

        # API gateway

        api = aws_apigateway.RestApi(
            self,
            "PhotoFrameAPI",
            binary_media_types=["*/*"],
            description="API for Photo Frame to retrieve images",
            deploy=False,
            endpoint_configuration=aws_apigateway.EndpointConfiguration(
                types=[aws_apigateway.EndpointType.REGIONAL]
            ),
        )

        api_items = api.root.add_resource("image")
        deployment = aws_apigateway.Deployment(
            self,
            "PhotoFrameDefaultDeployment",
            description="Photo Frame Deployment",
            api=api,
        )

        auth = aws_apigateway.RequestAuthorizer(
            self,
            "PhotoFrameRequestAuthorizer",
            handler=api_authorizer_fn,
            identity_sources=[aws_apigateway.IdentitySource.header("x-api-token")],
        )
        api_items.add_method(
            "GET",
            authorizer=auth,
            integration=aws_apigateway.LambdaIntegration(
                photo_handler_fn,
                content_handling=aws_apigateway.ContentHandling.CONVERT_TO_BINARY,
            ),
        )
        # Logging for API Gateway
        api_log_group = aws_logs.LogGroup(
            self, "PhotoFrameAPILog", retention=aws_logs.RetentionDays.ONE_WEEK
        )
        stage = aws_apigateway.Stage(
            self,
            "PhotoFrameStage",
            deployment=deployment,
            stage_name="public",
            access_log_destination=aws_apigateway.LogGroupLogDestination(api_log_group),
            access_log_format=aws_apigateway.AccessLogFormat.json_with_standard_fields(
                caller=False,
                http_method=True,
                ip=True,
                protocol=True,
                request_time=True,
                resource_path=True,
                response_length=True,
                status=True,
                user=True,
            ),
        )

        # WAF
        rules = [
            WafRule(
                name="WafIpreputation",
                rule_name="AWSManagedRulesAmazonIpReputationList",
                priority=1,
                metric_name="aws_reputation",
                excluded_rules=[],
            ),
            WafRule(
                name="WafAnony",
                rule_name="AWSManagedRulesAnonymousIpList",
                priority=2,
                metric_name="aws_anony",
                excluded_rules=["HostingProviderIPList"],
            ),
            WafRule(
                name="WafCommonRule",
                rule_name="AWSManagedRulesCommonRuleSet",
                priority=3,
                metric_name="aws_common",
                excluded_rules=["NoUserAgent_HEADER"],
            ),
            WafRule(
                name="WafBotControl",
                rule_name="AWSManagedRulesBotControlRuleSet",
                priority=4,
                metric_name="aws_bot",
                excluded_rules=["SignalNonBrowserUserAgent", "CategoryHttpLibrary"],
            ),
        ]

        waf_rules = [make_waf_rule(rule) for rule in rules]

        web_acl = aws_wafv2.CfnWebACL(
            self,
            "PhotoFrameWebACL",
            default_action=aws_wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            scope="REGIONAL",
            visibility_config=aws_wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="webACL",
                sampled_requests_enabled=True,
            ),
            name="PhotoFrameACL",
            rules=waf_rules,
        )

        resource_arn = (
            f"arn:aws:apigateway:{api.env.region}::/"
            f"restapis/{api.rest_api_id}/stages/{stage.stage_name}"
        )
        aws_wafv2.CfnWebACLAssociation(
            self,
            "PhotoFrameACLAssociation",
            web_acl_arn=web_acl.attr_arn,
            resource_arn=resource_arn,
        )

        cfn_log_group = aws_logs.CfnLogGroup(
            self,
            "PhotoFrameWafLogs",
            log_group_name="aws-waf-logs-photoframe",
            retention_in_days=30,
        )

        aws_wafv2.CfnLoggingConfiguration(
            self,
            "PhotoFrameLoggingConfig",
            log_destination_configs=[
                f"arn:aws:logs:{scope.region}:"
                f"{scope.account}:log-group:{cfn_log_group.log_group_name}"
            ],  # noqa
            resource_arn=web_acl.attr_arn,
            redacted_fields=[
                aws_wafv2.CfnLoggingConfiguration.FieldToMatchProperty(
                    single_header={"Name": "x-api-token"},
                )
            ],
        )


def make_waf_rule(rule: WafRule):
    return aws_wafv2.CfnWebACL.RuleProperty(
        name=rule.name,
        priority=rule.priority,
        visibility_config=aws_wafv2.CfnWebACL.VisibilityConfigProperty(
            cloud_watch_metrics_enabled=True,
            metric_name=rule.metric_name,
            sampled_requests_enabled=True,
        ),
        override_action=aws_wafv2.CfnWebACL.OverrideActionProperty(none={}),
        statement=aws_wafv2.CfnWebACL.StatementProperty(
            managed_rule_group_statement=aws_wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                name=rule.rule_name,
                vendor_name="AWS",
                excluded_rules=[
                    aws_wafv2.CfnWebACL.ExcludedRuleProperty(name=excluded_rule_name)
                    for excluded_rule_name in rule.excluded_rules
                ],
            )
        ),
    )
