import json
import os.path
import unittest
from typing import Dict
from unittest.mock import patch

from aws_cdk import App


from backend.component import Backend


ENV_VARIABLES = {"test": "test"}


def get_mock_context() -> Dict:
    return {"prod": {"log_level": "INFO"}}


class AppTest(unittest.TestCase):
    @classmethod
    @patch.dict(os.environ, ENV_VARIABLES)
    def setUpClass(
        cls,
    ):
        app = App(context=get_mock_context())
        stack_class = Backend(app, "PhotoFrameService")
        stack = app.synth().get_stack_by_name("PhotoFrameService")

        cls.template = json.dumps(stack.template)
        cls.stack_class = stack_class

    def test_s3_buckets_configured(self):
        stack = json.loads(self.template)
        buckets = [
            v for k, v in stack["Resources"].items() if v["Type"] == "AWS::S3::Bucket"
        ]
        self.assertEqual(1, len(buckets))