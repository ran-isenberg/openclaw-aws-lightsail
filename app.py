#!/usr/bin/env python3
import aws_cdk as cdk

from cdk.constants import REGION
from cdk.openclaw_stack import OpenClawStack

app = cdk.App()

OpenClawStack(
    app,
    'OpenClawStack',
    env=cdk.Environment(region=REGION),
)

app.synth()
