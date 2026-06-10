#!/usr/bin/env python3
import os

import aws_cdk as cdk

from medorra_backend.medorra_backend_stack import MedorraBackendStack

PREFIX = "Medorra"

app = cdk.App()
MedorraBackendStack(app, "MedorraBackendStack", prefix=PREFIX,
    env=cdk.Environment(account="094413394439", region="ap-southeast-1"),
    )

app.synth()
