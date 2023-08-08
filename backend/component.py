from typing import Any
import os

import aws_cdk as cdk
from constructs import Construct
from dacite import from_dict


from backend.storage.infrastructure import Storage
from backend.api.infrastructure import API
from backend.stack_helpers.stack_helpers import Environment
from backend.iot.infrastructure import IOT


class Backend(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        **kwargs: Any,
    ):
        super().__init__(scope, id_, **kwargs)

        # Set up config_env from cdk.json context
        config = dict(self.node.try_get_context(key="prod"))
        config_env: Environment = from_dict(data_class=Environment, data=config)  # noqa

        storage = Storage(self, "Storage")
        API(self, "API", storage.s3_bucket)
        IOT(self, "IOT")
