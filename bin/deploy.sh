#!/bin/bash

export LOG_LEVEL=INFO

cdk bootstrap
cdk deploy --require-approval never --all
