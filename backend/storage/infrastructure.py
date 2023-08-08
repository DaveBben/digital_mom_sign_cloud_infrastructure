import json
import os

from aws_cdk import (
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    CfnOutput,
    aws_iam as iam,
)
from constructs import Construct


BASE_FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class Storage(Construct):
    def __init__(self, scope: Construct, id_: str):
        super().__init__(scope, id_)

        # Set up a bucket
        self.s3_bucket = s3.Bucket(
            self,
            "PhotoFrameFilesBucket",
            bucket_name="photo-frame-files",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # files in public folder
        full_file_path = os.path.join(BASE_FILE_PATH, "public/")

        s3deploy.BucketDeployment(
            self,
            "PhotoFrameFilesBucketDeployment",
            sources=[s3deploy.Source.asset(full_file_path)],
            destination_bucket=self.s3_bucket,
            destination_key_prefix="public",
        )

        # Bucket Policy that allows access to anything
        # in the /public directory.
        bucket_read_policy = iam.ManagedPolicy(
            self,
            "photo_frame_files_s3_policy",
            description="Policy to read from Data Bucket",
            statements=[
                iam.PolicyStatement(
                    sid="ListBucket",
                    effect=iam.Effect.ALLOW,
                    actions=["s3:ListBucket"],
                    conditions={"StringLike": {"s3:prefix": "public/*"}},
                    resources=[self.s3_bucket.bucket_arn],
                ),
                iam.PolicyStatement(
                    sid="ReadObject",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                    ],
                    resources=[f"{self.s3_bucket.bucket_arn}/public/*"],
                ),
            ],
        )

        CfnOutput(
            self,
            "PhotoFrameBucketExport",
            export_name="photo-frame-bucket-arn",
            description="S3 ARN of Photo Frame Files Bucket",
            value=self.s3_bucket.bucket_arn,
        )
        CfnOutput(
            self,
            "PhotoFrameBucketExportPolicyExport",
            description="Add this policy to service role to read from the PhotoFrames Bucket",
            export_name="photo-frame-bucket-read-policy-arn",
            value=bucket_read_policy.managed_policy_arn,
        )
